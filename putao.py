# coding: utf8
"""葡萄 (putao, grape): Poor man's UTAU."""

import json
import pathlib
import re
import tempfile
from typing import List, Tuple, Union

import numpy as np
import soundfile
import sox

__version__ = "0.0.1a0"

RE_PITCH = re.compile(r"^([cdefgab][#b]?)(\d)$")
RE_LYRIC = re.compile(r"^(\w+)<(.*),(\d+(?:\.\d+)?)>$")

# assuming C scale
PIANO_SCALE = {
    n: c
    for c, n in enumerate(
        ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "bb", "b"], start=1
    )
}

VOICEBANK_CONFIG = "putao.json"


def _parse_note(note):
    try:
        key, octave = RE_PITCH.findall(note)[0]
        offset = PIANO_SCALE.get(key)
        if offset is None:
            raise IndexError
    except IndexError:
        return {}

    return {
        "key": key,
        "octave": int(octave),
        # so we won't multiply by 0.
        # (A note like 'A0' may be used.)
        "offset": ((int(octave) + 1) * 12) + offset,
    }


class Lyric:
    """A .wav file of a syllable pitched to a musical note.

    Args:
        wav_file: Path to the wav file.

        notes: A two-tuple of the original note of the wav file and the note to pitch the wav file to in scientific pitch notation.
            i.e ('C#3', 'Bb3') (c sharp, octave 3 -> b flat, octave 3).

        duration: How long the wav file should be streched to.

    Attributes:
        duration (float): How long the wav file is.
        new_duration (float): How long the wav file will be stretched to.
        note (dict): The original note of the wav file.
        new_note (dict): The pitch-shifted note of the wav file.

    Raises:
        ValueError, if one or both of the notes are invalid.
    """

    def __init__(
        self,
        wav_file: Union[str, pathlib.Path],
        notes: Tuple[str, str],
        duration: float,
    ) -> None:
        self._wav_file = pathlib.Path(wav_file)

        self.duration = sox.file_info.duration(self._wav_file)
        self.new_duration = duration

        self.note = _parse_note(notes[0].lower())
        self.new_note = _parse_note(notes[1].lower())

        if not (self.note and self.new_note):
            raise ValueError(f"invalid note(s): {', '.join(notes)}")

    def render(self) -> Tuple[np.ndarray, float]:
        """Render the note from the wav file.

        Returns:
            A numpy array representing the rendered note (as a wav file), and the sample rate.
        """

        tfm = sox.Transformer()

        # shift pitch using relative offset
        tfm.pitch(self.new_note["offset"] - self.note["offset"])

        wav, sample_rate = soundfile.read(str(self._wav_file))

        if self.new_duration is not None:
            # calculate the ratio of the two durations
            ratio = self.duration / self.new_duration
            # wav = rubberband.time_stretch(wav, sample_rate, ratio)
            tfm.tempo(ratio)

        return tfm.build_array(input_array=wav, sample_rate_in=sample_rate), sample_rate


class Song:
    """A song composed of lyrics.

    Args:
        voicebank: The path to the voicebank to use.

    Attributes:
        lyrics (List[Lyric]): The lyrics in the song.
    """

    def __init__(self, voicebank: Union[str, pathlib.Path] = ".") -> None:
        self._voicebank = pathlib.Path(voicebank)

        with (self._voicebank / VOICEBANK_CONFIG).open() as f:
            self._config = json.load(f)

        self.lyrics: List[Lyric] = []

    @property
    def syllables(self):
        return set(self._config["syllables"])

    def lyric(self, syllable: str, note: str, duration: float) -> None:
        """Add lyrics to the song.

        Args:
            syllable: The syllable to use.
                For a set of available syllables, use the attribute .syllables.
            note: The note to pitch the syllable to as letter notation,
                i.e 'Bb3' (b flat, octave 3).
            duration: How long to hold the syllable for.
                The syllable will be streched/shortened to this duration.

        Raises:
            ValueError, if the syllable does not exist.
        """

        if syllable not in self.syllables:
            raise ValueError(f"syllable {syllable} does not exist")

        syllable_conf = self._config["syllables"][syllable]

        self.lyrics.append(
            Lyric(
                self._voicebank / syllable_conf["path"],
                (syllable_conf["note"], note),
                duration,
            )
        )

    def render(self, path: Union[str, pathlib.Path]) -> None:
        """Render this song to a wav file.

        Args:
            path: The path to the wav file.
        """

        wavfiles = []

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = pathlib.Path(_tempdir)

            for count, note in enumerate(self.lyrics):
                render, sample_rate = note.render()

                wavfile_path = str(tempdir / f"{count}.wav")
                wavfiles.append(wavfile_path)

                soundfile.write(wavfile_path, render, sample_rate)

            cbn = sox.Combiner()
            cbn.build(wavfiles, str(path), "concatenate")

    @staticmethod
    def from_file(path: Union[str, pathlib.Path], *args, **kwargs):
        """Load a song from a putao song file.

        Args:
            path: The path to the song file.
            *args: Passed to __init__().
            **kwargs: Passed to __init__().

        Raises:
            ValueError, if the song file is syntactically incorrect.
        """
        song = Song(*args, **kwargs)

        with pathlib.Path(path).open() as f:
            for line, lyrics in enumerate(f.readlines()):
                for pos, lyric in enumerate(lyrics.split()):
                    try:
                        syllable, note, duration = RE_LYRIC.findall(lyric)[0]
                    except ValueError:
                        raise ValueError(
                            f"invalid lyric {lyric} (line {line}, pos {pos})"
                        )

                    song.lyric(syllable, note, float(duration))

        return song
