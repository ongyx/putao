from typing import Annotated, Any, Self

import attrs
import cattrs

import numpy as np

from ..oto import Voicebank, Pitch, Frq

from ._conv import converter


@attrs.define
class Note:
    """A pitched lyric in a song. All int values are in miliseconds unless specified otherwise.

    Attributes:
        length: How long the note should be.
        lyric: The sample to use.
        notenum: The MIDI note number to pitch the sample to.
        preutterance: Region where the sample should play before the actual note start.
            If None, the voicebank's preutterance is used.
        voiceoverlap: Where the previous note's vowel fades out.
            If None, the voicebank's overlap is used.
    """

    length: int
    lyric: str
    notenum: int
    preutterance: float | None = None
    voiceoverlap: float | None = None

    def is_rest(self) -> bool:
        """Check if the note is a rest."""

        return self.lyric == "R"

    def duration(self, bpm: float) -> float:
        """Get the duration of the note in milliseconds.

        Args:
            bpm: The beats per minute.

        Returns:
            The millisecond duration.
        """

        # In UTAU, note lengths are represented in 4/4 as multiples of 30, where a whole note is 480.
        beats = (self.length / 480) * 4
        bpms = bpm / 60 / 1000

        return beats / bpms

    def to_dict(self) -> dict[str, str]:
        """Serialize the note to a dict.

        Returns:
            A dict suitable for serialization as part of a UST.
        """

        config = {k: str(v) for k, v in converter.unstructure(self).items()}

        # Preutterance must be present anyway.
        config.setdefault("preutterance", "")

        return config

    @classmethod
    def from_dict(cls, note: dict[str, str]) -> Self:
        """Parse a note from a dict.

        Args:
            note: The note configuration in the UST.

        Returns:
            The parsed note.
        """

        # Remove preutterance if it is empty.
        if note.get("preutterance") == "":
            note = note.copy()
            del note["preutterance"]

        return converter.structure(note, cls)
