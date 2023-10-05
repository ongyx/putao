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

    for segment in SILENCE[::2500]:
        assert len(segment) == 2500


def test_segment_channels():
    stereo = SILENCE.set_channels(2)
    assert stereo.channels == 2

    mono = stereo.set_channels(1)
    assert mono.channels == 1


def test_segment_immutable():
    with pytest.raises(ValueError):
        SILENCE.array[0] = 0


def test_segment_mutable():
    with SILENCE.mutable() as silence:
        silence[:5000].array[:] = 0


def test_segment_append():
    double_silence = SILENCE + SILENCE

    assert len(double_silence) == len(SILENCE) * 2


def test_segment_spawn():
    spawn = SILENCE.spawn()

    assert spawn is not SILENCE
