import io

import pytest

from putao.oto.frq import Frq, _MAGIC

FORTY_TWO = bytes(
    [
        0x0,
        0x0,
        0x0,
        0x0,
        0x0,
        0x0,
        0x45,
        0x40,
    ]
)


TEST_FRQ = bytes(
    [
        # Magic number.
        *_MAGIC,
        # Number of samples per frame (256 by default).
        0x0,
        0x1,
        0x0,
        0x0,
        # Average F0.
        *FORTY_TWO,
        # Padding.
        *([0x0] * 16),
        # Number of frames.
        0x1,
        0x0,
        0x0,
        0x0,
        # Frame F0.
        *FORTY_TWO,
        # Frame amplitude.
        *FORTY_TWO,
    ]
)


def test_frq_load():
    fmap = Frq.loads(TEST_FRQ)

    assert fmap.samples == 256
    assert fmap.average == 42

    frame = fmap.frames[0]
    assert frame["frequency"] == 42
    assert frame["amplitude"] == 42


def test_frq_dump():
    fmap = Frq.loads(TEST_FRQ)

    output = fmap.dumps()

    assert output == TEST_FRQ
