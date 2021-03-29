# coding: utf8
"""Utility functions are kept here."""

import collections
import io
import math
import pathlib
import re
import wave
from typing import Union

import numpy as np
import soundfile
from pydub import AudioSegment

from .exceptions import ConversionError


RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

# in semitones
KEYS = {"c": 1, "d": 3, "e": 5, "f": 6, "g": 8, "a": 10, "b": 12}
NUM_KEYS = {v: k for k, v in KEYS.items()}


_note_length = collections.namedtuple(
    "note_length", "whole half quarter eighth sixteenth thirty_second sixty_fourth"
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
            self.semitone = value
        else:
            self.semitone = getattr(self, f"_from_{fmt}")(value)

        if self.semitone is None:
            raise ConversionError(f"invalid input: {value}")

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
        return round(12 * math.log2(hz / 440) + 58)


def srate(wav: Union[str, pathlib.Path]) -> int:
    """Get the sample rate of a wavfile."""

    return wave.open(open(wav, "rb")).getframerate()


def arr2seg(array: np.ndarray, srate: int) -> AudioSegment:
    """Convert a (numpy) wav array to a audio segment.

    Args:
        array: The wav array to convert.
        srate: The sample rate of the wav.

    Returns:
        The pydub audiosegment.
    """

    buf = io.BytesIO()
    soundfile.write(buf, array, srate, format="wav")

    return AudioSegment.from_file(buf, format="wav")


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

    return int(((60 / bpm) * (NOTE_LENGTH.quarter / length)) * 1000)
