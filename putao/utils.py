# coding: utf8

import collections
import re
from typing import Optional

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
