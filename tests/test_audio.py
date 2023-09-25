import numpy as np
import pytest

from putao import audio

SILENCE = audio.Segment.silent(10000)


def test_segment_len():
    # 10s -> 10000ms
    assert len(SILENCE) == 10000


def test_segment_slice():
    part = SILENCE[:5000]
    assert isinstance(part, audio.Segment)
    assert len(part) == 5000
