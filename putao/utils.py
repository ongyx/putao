# coding: utf8

import collections
import math
import re
from typing import Optional

import numpy as np

RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

# in semioctaves
KEYS = {"c": 1, "d": 3, "e": 5, "f": 6, "g": 8, "a": 10, "b": 12}

_note_length = collections.namedtuple(
    "note_length", "whole half quarter eighth sixteenth"
)
NOTE_LENGTH = _note_length(1, 2, 4, 8, 16)


def semitone(note: str) -> Optional[int]:
    """Parse a absoulute semitone value from a note.

    Args:
        note: The note in scientific pitch notation, i.e 'C4' (key C, octave 4).

    Returns:
        The absolute semitone value, as an int, or None if the note is invalid.
    """

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


def duration(length: int, bpm: int) -> float:
    """Calculate the duration of a note (how long it takes to play).
    One beat is defined as a quarter note.

    Args:
        length: A note length value from the NOTE_LENGTH namedtuple,
            i.e NOTE_LENGTH.whole (one note), NOTE_LENGTH.half (half note), etc.
        bpm: The tempo of the note in beats per minute.
    """

    return (60 / bpm) * (NOTE_LENGTH.quarter / length)


def semitone_to_hz(semitone: int) -> float:
    """Calculate hertz from semitones."""

    return math.pow(math.pow(2, 1 / 12), semitone - 49) * 440


def pitch(wav: np.ndarray, sr: int) -> float:
    """Calculate the pitch of a wavfile using autocorrelation.

    Args:
        wav: The wavfile as a numpy array.
        sr: The sample rate of the wavfile.

    Returns:
        The pitch in semitones.
    """
    wav = wav.copy()  # don't overwrite original

    signal = np.correlate(wav, wav, mode="full")[len(wav) - 1 :]

    low = int(sr / semitone_to_hz(12))
    high = int(sr / semitone_to_hz(120))

    signal[:low] = 0
    signal[high:] = 0

    pitch_hz = float(sr) / signal.argmax()

    pitch_semitones = (12 * math.log2(pitch_hz / 440)) + 49

    return pitch_semitones
