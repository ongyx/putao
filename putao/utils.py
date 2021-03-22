# coding: utf8

import collections
import hashlib
import math
import re

from pydub import AudioSegment

from putao.exceptions import ConversionError

RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

# in semitones
KEYS = {"c": 1, "d": 3, "e": 5, "f": 6, "g": 8, "a": 10, "b": 12}
NUM_KEYS = {v: k for k, v in KEYS.items()}

_note_length = collections.namedtuple(
    "note_length", "whole half quarter eighth sixteenth thirty_second sixty_fourth"
)
NOTE_LENGTH = _note_length(1, 2, 4, 8, 16, 32, 64)

SAMPLE_RATE = 44100
# stereo audio
CHANNELS = 2


class Pitch:
    """A numerical representation of a musical pitch.
    This class mainly serves to convert between different formats.

    Args:
        note: The pitch in scientific pitch notation, i.e C4 (key C, octave 4), C#4 (sharp), Cb4 (flat).
        semitone: The pitch in absolute number of semitones from C0, i.e 1 (C0), 49 (C4).
        hz: The pitch in Hertz, i.e 440 hz (C4).

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
        key_number = self.semitone % 12
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

    # A4 is note 58 here because the semitone is absolute (from C0, semitone = 1).
    @property
    def hz(self) -> float:
        return math.pow(math.pow(2, 1 / 12), self.semitone - 58) * 440

    @classmethod
    def _from_hz(cls, hz):
        return int(12 * math.log2(hz / 440) + 58)


def filesafe(name: str) -> str:
    """Hash name with the SHA1 algorithm, returning a slug suitable for a filename."""

    return hashlib.sha1(name.encode("utf8")).hexdigest()


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
