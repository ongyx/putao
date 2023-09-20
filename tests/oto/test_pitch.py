import pytest

from putao.oto import Pitch


def test_pitch():
    # Unorthodox way to say 'A4'.
    assert Pitch.parse("G##4").frequency == 440


def test_pitch_midi():
    assert Pitch.from_midi(60).midi == 60
