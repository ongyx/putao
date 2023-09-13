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

RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

_note_length = collections.namedtuple(
    "_note_length", "whole half quarter eighth sixteenth thirty_second sixty_fourth"
)
NOTE_LENGTH = _note_length(1, 2, 4, 8, 16, 32, 64)

KEYS = ["c", "c#", "d", "d#", "e", "f", "f#", "g", "g#", "a", "a#", "b"]


class Pitch:
    def __init__(self):
        self.hz = 0.0

    @property
    def midi(self) -> int:
        return int((12 * math.log2(self.hz / 440)) + 69)

    @midi.setter
    def midi(self, note: int):
        self.hz = 440 * (2 ** ((note - 69) / 12))

    @property
    def spn(self) -> str:
        semitone = self.midi

        # the octave range of spn starts from C-1
        octave = (semitone // 12) - 1
        key = KEYS[semitone % 12]

        return f"{key}{octave}"

    @spn.setter
    def spn(self, note: str):
        key, accidental, octave = RE_NOTE.findall(note)[0]

        semitone = (int(octave) * 12) + KEYS.index(key.lower())
        if accidental == "#":
            semitone += 1
        elif accidental == "b":
            semitone -= 1

        self.midi = semitone


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
