import dataclasses
from typing import Any, Self


@dataclasses.dataclass(slots=True)
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

    def serialize(self) -> dict[str, str]:
        note = {
            "length": str(self.length),
            "lyric": self.lyric,
            "notenum": str(self.notenum),
        }

        if self.preutterance is not None:
            note["preutterance"] = str(self.preutterance)
        else:
            # Preutterance must be present anyway.
            note["preutterance"] = ""

        if self.voiceoverlap is not None:
            note["voiceoverlap"] = str(self.voiceoverlap)

        return note

    @classmethod
    def parse(cls, note: dict[str, str]) -> Self:
        kwargs: dict[str, Any] = {
            "length": int(note["length"]),
            "lyric": note["lyric"],
            "notenum": int(note["notenum"]),
        }

        if preutterance := note.get("preutterance"):
            kwargs["preutterance"] = float(preutterance)

        if voiceoverlap := note.get("voiceoverlap"):
            kwargs["voiceoverlap"] = float(voiceoverlap)

        return cls(**kwargs)
