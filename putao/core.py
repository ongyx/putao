# coding: utf8

import abc
import json
import logging
import pathlib
import tempfile
from collections.abc import Mapping
from typing import List, Tuple, Union

import numpy as np
import soundfile
import sox

from putao import backend, utils
from putao.exceptions import LyricError

logging.getLogger("sox").setLevel(logging.ERROR)

VOICEBANK_CONFIG = "voicebank.json"
SAMPLE_RATE = 44100


class Note(abc.ABC):
    """A musical pitch.

    Args:
        pitch: The relative semitone difference between the original pitch and the pitch to tune to.
        duration: How long the note should be streched to.

    Attributes:
        type (str): The type of note. Should be overwritten in subclasses.
        pitch (int): See args.
        duration (float): See args.
    """

    type = "Note"

    def __init__(self, pitch: int, duration: float):
        self.pitch = pitch
        self.duration = duration

    def dump(self) -> dict:
        """Dump a dict representation of the note.

        Returns:
            A dict with at least the keys 'type', 'pitch' and 'duration',
            corrosponding to self.type, self.pitch and self.duration.

        Raises:
            ValueError, if self.type was not set by subclasses.
        """
        if not self.type:
            raise ValueError("self.type was not set in a subclass")

        return {"type": self.type, "pitch": self.pitch, "duration": self.duration}

    @abc.abstractmethod
    def render(self) -> Tuple[np.ndarray, float]:
        """Render the pitch.

        Returns:
            A numpy array representing the rendered note and the sample rate.
        """


class Rest(Note):

    type = "rest"

    def render(self):
        return np.arange(self.duration * SAMPLE_RATE), SAMPLE_RATE


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
        tfm.pitch(self.pitch)

        wav, sample_rate = soundfile.read(str(self._wav_file))

        if self.duration is not None:
            # calculate the ratio of the two durations
            ratio = self._duration / self.duration
            # wav = rubberband.time_stretch(wav, sample_rate, ratio)
            tfm.tempo(ratio)

        tfm.pad(0.01, 0.01)

        return tfm.build_array(input_array=wav, sample_rate_in=sample_rate), sample_rate


class Voicebank(Mapping):
    """A voicebank.

    Args:
        path: The path to the voicebank.

    Attributes:
        path: See args.
        config: The voicebank's config.
    """

    def __init__(self, path: Union[str, pathlib.Path]):
        self.path = pathlib.Path(path)

        with (self.path / VOICEBANK_CONFIG).open() as f:
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
        notes (List[Lyric]): The notes in the track.
    """

    def __init__(self, voicebank: Voicebank):
        self._voicebank = voicebank
        self.notes: List[Note] = []

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
            duration: How long to hold the syllable for.
                The syllable will be streched/shortened to this duration.

        Raises:
            LyricError, if the syllable does not exist or its pitch is invalid.
        """

        if syllable not in self.syllables:
            raise LyricError(f"syllable {syllable} does not exist")

        syllable_note = self._voicebank["syllables"][syllable]

        syllable_pitch = utils.semitone(syllable_note)

        if syllable_pitch is None:
            raise LyricError(f"invalid pitch: {syllable_pitch}")

        self.notes.append(
            LyricalNote(
                self._voicebank.path / f"{syllable}.wav",
                pitch - syllable_pitch,
                duration,
            )
        )

    def rest(self, duration: float):
        """Add a break in-between notes (specifically, after the last note that was added).
        Note that multiple rests after one another are culminative.

        Args:
            duration: How long to rest for.
        """

        self.notes.append(Rest(0, duration))

    def render(self, path: Union[str, pathlib.Path]):
        """Render this track to a wav file.

        Args:
            path: The path to the wav file.
        """

        wavfiles = []

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = pathlib.Path(_tempdir)

            for count, note in enumerate(self.notes):
                render, sample_rate = note.render()

                wavfile_path = str(tempdir / f"{count}.wav")
                wavfiles.append(wavfile_path)

                soundfile.write(wavfile_path, render, sample_rate)

            cbn = sox.Combiner()
            cbn.build(wavfiles, str(path), "concatenate")


class Project:
    """A project made of multiple tracks."""

    def __init__(self, voicebank: Union[str, pathlib.Path] = "."):

        self.voicebank = Voicebank(voicebank)
        self.tracks: List[Track] = []

    def new_track(self) -> Track:
        """Create a new track in this project.

        Returns:
            The track object.
        """

        self.tracks.append(Track(self.voicebank))
        return self.tracks[-1]

    def dump_dict(self) -> dict:
        """Dump this project file, as a dict."""

        return {
            "tracks": [[note.dump() for note in track.notes] for track in self.tracks]
        }

    def load_dict(self, data: dict):
        """Load a putao project file, as a dict.

        Args:
            data: The dict to load.
        """

        for track in data["tracks"]:

            track_obj = self.new_track()

            for note in track:

                if note["type"] == "rest":
                    track_obj.rest(note["duration"])
                else:
                    track_obj.note(
                        *[note[f] for f in ("syllable", "pitch", "duration")]
                    )

    def create(self, lyrics: List[List[str]], data: bytes, fmt: str):
        """Initalise this project with external data.

        Args:
            lyrics: A list of list of lyrics to add.
                The outer list maps to tracks, and the inner list maps to notes.
            data: The source to load the notes from as bytes.
            fmt: The format of the source.
                Currently, only 'mml' is supported.
        """

        project_data = backend.loads(data, fmt)
        count = 0

        for track_num, track in enumerate(lyrics):
            for lyric in track:
                note = project_data[track_num][count]
                if note["type"] != "rest":
                    project_data[track_num][count]["syllable"] = lyric
                count += 1

        self.load_dict({"tracks": project_data})

    def render(self, path: Union[str, pathlib.Path]):
        """Render all tracks in this project to a single wavfile.

        Args:
            path: Where to save the rendered wavfile.
        """

        if len(self.tracks) < 2:
            self.tracks[0].render(path)
            return

        track_paths = []
        cbn = sox.Combiner()

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = pathlib.Path(_tempdir)

            for count, track in enumerate(self.tracks):
                track_path = tempdir / f"{count}.wav"
                track_paths.append(str(track_path))
                track.render(track_path)

            cbn.build(track_paths, str(path), "mix")
