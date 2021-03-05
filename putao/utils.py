# coding: utf8

import collections
import math
import pathlib
import re
import tempfile
from typing import Optional, Tuple

import numpy as np
import sox
import soundfile

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


def note_to_hz(note: str) -> float:
    """Calculate hertz from notes."""
    semitones = semitone(note)
    if semitones is not None:
        return semitone_to_hz(semitones)

    return 0.0


def tune_sample(y: np.ndarray, sr: float, note: str = "C4") -> Tuple[np.ndarray, float]:
    """Tune a sample to the correct pitch.

    Args:
        y: The original sample (as a numpy array).
        sr: The sample rate of the sample.
        note: The note to tune the sample to.
            Defaults to C4 (middle C).

    Returns:
        The tuned sample as a numpy array, and its sample rate.
    """

    with tempfile.TemporaryDirectory() as _tempdir:
        tempdir = pathlib.Path(_tempdir)
        sample_path = tempdir / "in.wav"
        sine_path = tempdir / "sine.wav"
        tuned_path = tempdir / "out.wav"

        soundfile.write(sample_path, y, sr)

        # create sine
        sine_wave = np.sin(2 * np.pi * note_to_hz(note) * np.arange(sr * 1.0) / sr)
        soundfile.write(sine_path, sine_wave, sr)

        cbn = sox.Combiner()
        cbn.build(
            [str(sample_path), str(sine_path)], str(tuned_path), combine_type="multiply"
        )

        return soundfile.read(tuned_path)
