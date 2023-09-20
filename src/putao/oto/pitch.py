import dataclasses
import re
from math import log2
from typing import Self

CONCERT_PITCH = 440

NOTES = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

ACCIDENTALS = {
    "#": 1,
    "##": 2,
    "b": -1,
    "bb": -2,
}

RE_SPN = re.compile(
    r"""
    ^

    # Note name.
    (?P<note>[a-gA-G])

    # Optional accidental.
    (?P<accidental>[\#|b]{1,2})?

    # Octave number from -1 to 9.
    (?P<octave>-1|\d)

    $
    """,
    re.VERBOSE,
)


@dataclasses.dataclass(slots=True)
class Pitch:
    """A musical pitch.

    Attributes:
        frequency: The frequency of the pitch in hertz.
    """

    frequency: float

    @classmethod
    def parse(cls, spn: str) -> Self:
        """Parse scientific pitch notation.

        Scientific pitch notation (SPN for short) specifies a musical pitch in the form of a note and octave.

        For example:
        * `A4` is A above middle C.
        * `C#5` is C sharp in the 5th octave.
        * `Gb6` is G flat in the 6th octave, enharmonically equivalent to F sharp.

        Args:
            spn: The SPN to parse.

        Returns:
            The parsed SPN as a pitch.

        Raises:
            ValueError: The SPN is invalid.
        """

        if match := RE_SPN.match(spn):
            note = NOTES[match["note"].upper()]

            accidental = ACCIDENTALS.get(match["accidental"], 0)

            # Since MIDI note numbers start from C-1, add 1 to get an octave we can multiply by.
            octave = int(match["octave"]) + 1

            return cls.from_midi(note + accidental + (octave * 12))

        raise ValueError(f"spn is invalid: {spn}")

    @classmethod
    def from_midi(cls, note: int) -> Self:
        """Create a pitch from a MIDI note number.

        Args:
            note: The MIDI note number.

        Returns:
            A pitch with its frequency corresponding to the MIDI note number.
        """

        pitch = cls(0)
        pitch.midi = note
        return pitch

    @property
    def midi(self) -> int:
        """The pitch's frequency as a MIDI note number."""

        return round(69 + (12 * log2(self.frequency / CONCERT_PITCH)))

    @midi.setter
    def midi(self, note: int):
        self.frequency = (2 ** ((note - 69) / 12)) * CONCERT_PITCH
