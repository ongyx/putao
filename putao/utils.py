# coding: utf8
"""Utility functions are kept here."""

import collections
import math
import pathlib
import re
import wave
from typing import Union

import numpy as np
import pyworld
from pydub import AudioSegment

from .exceptions import ConversionError


SAMPLE_RATE = 44100
CHANNELS = 2

RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

# in semitones
KEYS = {"c": 1, "d": 3, "e": 5, "f": 6, "g": 8, "a": 10, "b": 12}
NUM_KEYS = {v: k for k, v in KEYS.items()}

_note_length = collections.namedtuple(
    "_note_length", "whole half quarter eighth sixteenth thirty_second sixty_fourth"
)
NOTE_LENGTH = _note_length(1, 2, 4, 8, 16, 32, 64)


class Pitch:
    """A numerical representation of a musical pitch.
    This class mainly serves to convert between different formats.

    Args:
        note: The pitch in scientific pitch notation, i.e C4 (key C, octave 4), C#4 (sharp), Cb4 (flat).
        semitone: The pitch in absolute number of semitones from C0, i.e 1 (C0), 49 (C4).
        hz: The pitch in Hertz, i.e 440 hz (A4).

    Raises:
        ValueError, if exactly one of 'note', 'semitone' or 'hz' is not specified.
        ConversionError, if the format/input is invalid.
    """

    def __init__(self, **kwargs):
        ((fmt, value),) = kwargs.items()

        if fmt == "semitone":
            self._semitone = value
        else:
            self._semitone = getattr(self, f"_from_{fmt}")(value)

        if self._semitone is None:
            raise ConversionError(f"invalid input: {value}")

    @property
    def semitone(self) -> int:
        return round(self._semitone)

    @property
    def note(self) -> str:
        # the key 'b' has semitone value 12, so modulo will be 0
        key_number = (self.semitone % 12) or 12

        try:
            key = str(NUM_KEYS[key_number])
        except KeyError:
            key = f"{NUM_KEYS[key_number - 1]}#"

        return f"{key.upper()}{self.semitone // 12}"

    @classmethod
    def _from_note(cls, note):
        try:
            key, accidental, octave = RE_NOTE.findall(note)[0]
        except IndexError:
            return None

        semitone = KEYS[key.lower()]
        if accidental == "#":
            semitone += 1
        elif accidental == "b":
            semitone -= 1

        return (int(octave) * 12) + semitone

    @property
    def hz(self) -> float:
        # since scientific pitch notation starts from C0,
        # semitone values also start from 0.
        # so A4 is semitone 58.
        return math.pow(math.pow(2, 1 / 12), self.semitone - 58) * 440

    @classmethod
    def _from_hz(cls, hz):
        return 12 * math.log2(hz / 440) + 58


def srate(wav: Union[str, pathlib.Path]) -> int:
    """Get the sample rate of a wavfile."""

    return wave.open(open(wav, "rb")).getframerate()


def duration(length: int, bpm: int) -> int:
    """Calculate the duration of a note in miliseconds (how long it takes to play).
    One beat is defined as a quarter note.

    Args:
        length: A note length value from the NOTE_LENGTH namedtuple,
            i.e NOTE_LENGTH.whole (one note), NOTE_LENGTH.half (half note), etc.
        bpm: The tempo of the note in beats per minute.
    """

    if length not in NOTE_LENGTH:
        return 0

    # There are 60000 miliseconds in a minute.
    # Since bpm is beats per minute, bpm / 60000 equals the number of beats per milisecond.
    # Then, we invert to get miliseconds per beat.
    # Finally, we multiply it by quarter note length / note length,
    # because a beat is one quarter note.

    ms_per_beat = 1 / (bpm / 60000)
    return int(ms_per_beat * (NOTE_LENGTH.quarter / length))


def sine_f0(duration: float, srate: int) -> np.ndarray:
    """Return the f0 contour of a sine wave of duration seconds long."""

    sine_arr = np.sin(2 * np.pi * np.arange(srate * duration) * 440.0 / srate).astype(
        np.float64
    )

    f0 = pyworld.stonemask(sine_arr, *pyworld.dio(sine_arr, srate), srate)
    return f0


def _is_float(dtype):
    return dtype.kind in np.typecodes["AllFloat"]


def _is_int(dtype):
    return dtype.kind in np.typecodes["AllInteger"]


def scale(arr: np.ndarray, dtype: np.dtype) -> np.ndarray:
    """Scale a wavfile array to another format.

    Args:
        arr: The wavfile array to scale.
        to: The format to scale to, as a dtype.

    Returns:
        The scaled wavfile.
    """

    if np.can_cast(arr.dtype, dtype, casting="same_kind"):
        arr = arr.astype(dtype)

    else:
        # scale values
        if _is_int(arr.dtype) and _is_float(dtype):

            scale = np.iinfo(arr.dtype).max
            arr = (arr / scale).astype(dtype)

        elif _is_float(arr.dtype) and _is_int(dtype):

            scale = np.iinfo(dtype).max
            arr = (arr * scale).astype(dtype)

    return arr


def seg2arr(seg: AudioSegment) -> np.ndarray:
    """Convert an AudioSegment to a numpy array."""

    channels = seg.split_to_mono()
    samples = [c.get_array_of_samples() for c in channels]

    arr = np.array(samples).T.astype(np.float64)
    arr /= np.iinfo(samples[0].typecode).max

    return arr


def arr2seg(arr: np.ndarray, srate: int) -> AudioSegment:
    """Convert a numpy array to an AudioSegment."""

    # make sure arr is in 16-bit int format
    if not _is_int(arr.dtype):
        arr = scale(arr, np.dtype("int16"))

    return AudioSegment(
        arr.tobytes(),
        frame_rate=srate,
        sample_width=arr.dtype.itemsize,
        channels=len(arr.shape),
    )
