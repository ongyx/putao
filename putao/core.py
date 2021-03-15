# coding: utf8

import abc
import math
import json
import logging
import pathlib
import tempfile
from collections.abc import Mapping
from typing import Dict, IO, List, Tuple, Union, Optional

import numpy as np
import soundfile
import sox

from putao import backend
from putao.exceptions import LyricError

logging.getLogger("sox").setLevel(logging.ERROR)

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger("putao")

VOICEBANK_CONFIG = "voicebank.json"
SAMPLE_RATE = 44100
# stereo audio
CHANNELS = 2


class Note(abc.ABC):
    """A musical pitch.

    Args:
        og_pitch: The absolute semitone of the original pitch.
        pitch: The absolute semitone of the pitch to tune to.
        duration: How long the note should be streched to.

    Attributes:
        type (str): The type of note. Should be overwritten in subclasses.
        pitch (int): See args.
        duration (float): See args.
    """

    type = "note"

    def __init__(self, og_pitch: float, pitch: float, duration: float):
        self.og_pitch = og_pitch
        self.pitch = pitch
        self.duration = duration

    def __repr__(self):
        return f"Note(type={self.type}, pitch={self.pitch}, duration={self.duration})"

    def dump(self) -> dict:
        """Dump a dict representation of the note.

        Returns:
            A dict with at least the keys 'type', 'pitch' and 'duration',
            corrosponding to self.type, self.pitch and self.duration.
        """

        return {
            "type": self.type,
            "pitch": self.pitch,
            "duration": self.duration,
        }

    @abc.abstractmethod
    def render(self) -> Tuple[np.ndarray, float]:
        """Render the pitch.

        Returns:
            A numpy array representing the rendered note and the sample rate.
        """


class Rest(Note):

    type = "rest"

    def render(self):
        nframes = math.ceil(self.duration * SAMPLE_RATE)
        return np.zeros((nframes, CHANNELS)), SAMPLE_RATE


class LyricalNote(Note):
    """A .wav file of a syllable pitched to a musical pitch.

    Args:
        wav_file: Path to the wav file.
        *args: Passed to super().__init__.
        **kwargs: Passed to super().__init__.
    """

    def __init__(self, wav_file: Union[str, pathlib.Path], *args, **kwargs):
        self._wav_file = pathlib.Path(wav_file)

        super().__init__(*args, **kwargs)

        self._duration = sox.file_info.duration(self._wav_file)

    def dump(self):
        data = super().dump()
        data["syllable"] = self._wav_file.stem
        return data

    def render(self):
        tfm = sox.Transformer()

        # shift pitch using relative pitch
        tfm.pitch(self.pitch - self.og_pitch)
        # force 44.1khz sample rate & stereo channels
        tfm.convert(samplerate=SAMPLE_RATE, n_channels=CHANNELS)

        wav, sample_rate = soundfile.read(str(self._wav_file))

        # calculate the ratio of the two durations
        ratio = self._duration / self.duration
        if 0.1 < ratio < 100:
            # wav = rubberband.time_stretch(wav, sample_rate, ratio)
            tfm.tempo(ratio)

        return (
            tfm.build_array(
                input_array=wav,
                sample_rate_in=sample_rate,
            ),
            SAMPLE_RATE,
        )


class Voicebank(Mapping):
    """A voicebank.

    Args:
        path: The path to the voicebank.
        create: Whether or not to tune samples to C4 (middle C) and generate a new config.
            Defaults to False.

    Attributes:
        path: See args.
        config: The voicebank's config.
    """

    def __init__(self, path: Union[str, pathlib.Path]):
        self.path = pathlib.Path(path)
        self._config_path = self.path / VOICEBANK_CONFIG

        with self._config_path.open() as f:
            self.config = json.load(f)

    def __getitem__(self, key):
        return self.config[key]

    def __iter__(self):
        return iter(self.config)

    def __len__(self):
        return len(self.config)


class Track:
    """A track composed of notes.

    Args:
        voicebank: The voicebank object to use.

    Attributes:
        notes (List[Note]): The notes in the track.
    """

    def __init__(self, voicebank: Voicebank):
        self._voicebank = voicebank
        self._notes: List[Note] = []

    @property
    def syllables(self):
        return set(self._voicebank["syllables"])

    def note(self, syllable: str, pitch: int, duration: float):
        """Add notes to the track.

        Args:
            syllable: The syllable to use.
                For a set of available syllables, use the attribute .syllables.
            pitch: The absoulute semitone value of the pitch.
                i.e C4 (middle C) -> (4 * 12) + 1 = 49.
            duration: How long to hold the syllable for (in seconds).
                The syllable will be streched/shortened to this duration.

        Raises:
            LyricError, if the syllable does not exist or its pitch is invalid.
        """

        syllable_pitch = self._voicebank["syllables"].get(syllable)

        if syllable_pitch is None:
            raise LyricError(f"syllable {syllable} does not exist in current voicebank")

        note = LyricalNote(
            self._voicebank.path / f"{syllable}.wav",
            syllable_pitch,
            pitch,
            duration,
        )

        self._notes.append(note)

    def rest(self, duration: float):
        """Add a break in-between notes (specifically, after the last note that was added).
        Note that multiple rests after one another are culminative.

        Args:
            duration: How long to rest for.
        """

        rest = Rest(0, 0, duration)
        self._notes.append(rest)

    def render(self, to_filepath: Union[str, pathlib.Path]):
        """Render this track to a wavfile.

        Args:
            to_filepath: The path to output the rendered wavfile.
        """

        wavfiles = []

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = pathlib.Path(_tempdir)

            total = len(self._notes)

            for count, note in enumerate(self._notes, start=1):
                try:
                    render, sample_rate = note.render()
                except Exception as e:
                    _log.critical("SHIT: failed to render %s!!! (reason: %s)", note, e)
                    raise e

                _log.debug(
                    "[%s/%s] rendered %s",
                    count,
                    total,
                    note,
                )

                wavfile_path = str(tempdir / f"{count}.wav")
                wavfiles.append(wavfile_path)

                soundfile.write(wavfile_path, render, sample_rate)

            if len(wavfiles) >= 2:
                cbn = sox.Combiner()
                cbn.build(wavfiles, str(to_filepath), combine_type="concatenate")

            else:
                pathlib.Path(wavfiles[0]).rename(to_filepath)

    def dump(self) -> List[dict]:
        """Dump this track to a dict representation.
        It can be serialised to JSON and loaded back using '.load()'.

        Returns:
            A list of notes in this track as dicts.
        """

        return [note.dump() for note in self._notes]

    def load(self, notes: List[dict]):
        """Load notes into this track from a dict representation.

        Args:
            notes: The list notes previously dumped using '.dump()'.
        """

        for note in notes:

            if note["type"] == "rest":
                self.rest(note["duration"])
            else:
                self.note(*[note[f] for f in ("syllable", "pitch", "duration")])


class Project:
    """A project made of multiple tracks.

    Args:
        voicebank: The path to the voicebank to be used (for this project).

    Attributes:
        voicebank (Voicebank): The voicebank in use.
        tracks (Dict[str, Track]): The tracks in this project.
    """

    def __init__(self, voicebank: Union[str, pathlib.Path] = "."):

        self.voicebank = Voicebank(voicebank)
        self.tracks: Dict[str, Track] = {}

    def track(self, name: str, exists_ok: bool = True) -> Track:
        """Get a track in this project, creating it if it does not exist.

        Args:
            name: The track name.
            exists_ok: Whether or not to return the existing track, if any.
                Defaults to True.

        Returns:
            The track object.

        Raises:
            ValueError, if the track already exists and exists_ok is False.
        """

        if name in self.tracks:
            if exists_ok:
                return self.tracks[name]
            else:
                raise ValueError(f"track already exists: {name}")

        new_track = Track(self.voicebank)
        self.tracks[name] = new_track
        return new_track

    def new_track(self, name: str) -> Track:
        """Alias for '.track(name, exists_ok=False)'."""

        return self.track(name, exists_ok=False)

    def dump_dict(self) -> dict:
        """Dump this project as a dict."""

        return {"tracks": {name: track.dump() for name, track in self.tracks.items()}}

    def dump(self, fp: IO):
        """Dump this project to a file.

        Args:
            fp: The file object to dump to. Must be opened in write mode.
        """

        json.dump(self.dump_dict(), fp, indent=4)

    def load_dict(self, data: dict):
        """Load a project as a dict.

        Args:
            data: The dict to load.
        """

        for track_name, track_notes in data["tracks"].items():

            track = self.new_track(track_name)
            track.load(track_notes)

    def load(self, fp: IO):
        """Load a project from a file.

        Args:
            fp: The file object to load from. Must be opened in read mode.
        """

        self.load_dict(json.load(fp))

    def create(
        self, data: bytes, fmt: str, lyrics: Optional[Dict[str, List[str]]] = None
    ):
        """Initalise this project with external data.

        Args:
            data: The source to load the notes from as bytes.
            fmt: The format of the source.
            lyrics: A dict of list of lyrics to add. (track_name -> track_lyrics).
                If not None, lyrics already loaded from the backend will be overwritten.
                Defaults to None.
        """

        project_data = backend.loads(data, fmt)

        if lyrics is not None:
            for name, track in project_data.items():
                track_lyrics = lyrics[name]
                track_len = len(track)
                track_lyrics_len = len(track_lyrics)

                if track_lyrics_len < track_len:
                    track_lyrics.extend(
                        track_lyrics[-1] for _ in range(track_len - track_lyrics_len)
                    )

                for lyric_num, lyric in enumerate(track_lyrics):
                    note = track[lyric_num]
                    if note["type"] != "rest":
                        note["syllable"] = lyric

        self.load_dict({"tracks": project_data})

    def render(self, path: Union[str, pathlib.Path]):
        """Render all tracks in this project to a single wavfile.

        Args:
            path: Where to save the rendered wavfile.
        """

        if len(self.tracks) < 2:
            name = [*self.tracks][0]
            self.tracks[name].render(path)
            return

        track_paths = []
        cbn = sox.Combiner()

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = pathlib.Path(_tempdir)

            for count, (name, track) in enumerate(self.tracks.items()):
                _log.info(
                    "rendering track '%s' (total %s notes)", name, len(track._notes)
                )
                track_path = tempdir / f"{count}.wav"
                track_paths.append(str(track_path))
                track.render(track_path)

            cbn.build(track_paths, str(path), "mix")
