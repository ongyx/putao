# coding: utf8

import collections
import hashlib
import math
import re
from typing import Optional

from pydub import AudioSegment

RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

# in semioctaves
KEYS = {"c": 1, "d": 3, "e": 5, "f": 6, "g": 8, "a": 10, "b": 12}

_note_length = collections.namedtuple(
    "note_length", "whole half quarter eighth sixteenth thirty_second sixty_fourth"
)
NOTE_LENGTH = _note_length(1, 2, 4, 8, 16, 32, 64)

SAMPLE_RATE = 44100
# stereo audio
CHANNELS = 2


def filesafe(name: str) -> str:
    """Hash name with the SHA1 algorithm, returning a slug suitable for a filename."""

    return hashlib.sha1(name.encode("utf8")).hexdigest()


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


def semitone_to_hz(semitone: float) -> float:
    """Calculate hertz from semitones."""

    return math.pow(math.pow(2, 1 / 12), semitone - 49) * 440


def hz_to_semitone(hz: float) -> float:
    """Calculate semitones from hertz."""

    return 12 * math.log2(hz / 440) + 49


def note_to_hz(note: str) -> float:
    """Calculate hertz from notes."""
    semitones = semitone(note)
    if semitones is not None:
        return semitone_to_hz(semitones)

    return 0.0


def pitch_shift(audio: AudioSegment, semitones: int) -> AudioSegment:
    """Shift the pitch of the audio segment by semitones.
    (https://github.com/jiaaro/pydub/issues/157#issuecomment-252366466)

    Args:
        audio: The pydub audio segment to pitch-shift.
        semitones: How many semitones to shift (negative values will shift down).

    Returns:
        The pitch-shifted segment.
    """

    octaves = semitones / 12
    new_sr = int(audio.frame_rate * (2 ** octaves))

    pitch_shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sr})
    return pitch_shifted.set_frame_rate(SAMPLE_RATE)
