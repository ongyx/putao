# coding: utf8
"""Notes are the combination of a phenome, duration and pitch."""

from dataclasses import dataclass

from . import utau


@dataclass
class _NoteBase:
    duration: int


@dataclass
class Note(_NoteBase):
    pitch: int
    phenome: utau.Entry


@dataclass
class Rest(_NoteBase):
    pass
