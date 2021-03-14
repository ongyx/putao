# coding: utf8

import collections
import math
import re
import struct
import wave
from typing import IO, Optional, Union

import numpy as np

RE_NOTE = re.compile(r"^((?i:[cdefgab]))([#b])?(\d+)$")

# in semioctaves
KEYS = {"c": 1, "d": 3, "e": 5, "f": 6, "g": 8, "a": 10, "b": 12}

_note_length = collections.namedtuple(
    "note_length", "whole half quarter eighth sixteenth thirty_second sixty_fourth"
)
NOTE_LENGTH = _note_length(1, 2, 4, 8, 16, 32, 64)
CHUNKSIZE = 2048  # bigger values require more memory


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
    if length not in NOTE_LENGTH:
        return 0

    return (60 / bpm) * (NOTE_LENGTH.quarter / length)


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


def estimate_semitone(wav: Union[str, IO]) -> float:
    """Estimate the absolute semitone value of a wavfile by averaging frequencies found using a Fast Fourier Transform.
    (https://stackoverflow.com/a/2649540)

    NOTE: The wav file _must_ be mono (one channel only)!
    Because the channels are interleaved, numpy will complain about multiplying arrays of different dimentions.

    Args:
        wav: The wavfile to use.

    Returns:
        The semitone value, as a float.
    """

    wavfile = wave.open(wav)
    sample_width = wavfile.getsampwidth()
    sample_rate = wavfile.getframerate()

    window = np.blackman(CHUNKSIZE)

    # frequencies shouldn't be highr than this.
    upperbound = semitone_to_hz(88)

    frequencies = []

    while True:
        wav_chunk = wavfile.readframes(CHUNKSIZE)
        wav_len = len(wav_chunk) // sample_width

        if wav_len < CHUNKSIZE:
            break

        fmt = f"<{wav_len}h"
        wav_data = struct.unpack(fmt, wav_chunk)

        wav_array = np.array(wav_data) * window

        fft_data = abs(np.fft.rfft(wav_array)) ** 2
        fft_max = fft_data[1:].argmax() + 1

        if fft_max != len(fft_data) - 1:
            with np.errstate(divide="ignore", invalid="ignore"):
                y0, y1, y2 = np.log(fft_data[fft_max - 1 : fft_max + 2])
                x1 = (y2 - y0) * 0.5 / (2 * y1 - y2 - y0)
                frequency = (fft_max + x1) * sample_rate / CHUNKSIZE

        else:
            frequency = fft_max * sample_rate / CHUNKSIZE

        # discard invalid or impossible frequencies
        if frequency <= upperbound:
            frequencies.append(frequency)

    return hz_to_semitone(float(np.array(frequencies).mean()))
