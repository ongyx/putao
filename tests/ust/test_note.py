import pytest

from putao.ust import Note

NOTE = {
    "length": "480",
    "lyric": "R",
    "notenum": "60",
    "preutterance": "",
}


def test_note_from_dict():
    note = Note.from_dict(NOTE)
    assert note.length == 480
    assert note.duration(120) == 2000
    assert note.is_rest
    assert note.notenum == 60
    assert note.preutterance is None


def test_note_to_dict():
    note = Note.from_dict(NOTE)
    assert note.to_dict() == NOTE
