import pytest

from putao.audio import Segment
from putao.oto import Sample


def test_sample():
    sample = Sample.parse("あ.wav=あ,1,2,3,4,5")

    assert sample.file == "あ.wav"
    assert sample.alias == "あ"
    assert sample.offset == 1
    assert sample.consonant == 2
    assert sample.cutoff == 3
    assert sample.preutterance == 4
    assert sample.overlap == 5


def test_sample_negative():
    sample = Sample.parse("a.wav=a,-1,-2,-3,-4,-5")

    assert sample.file == "a.wav"
    assert sample.alias == "a"
    assert sample.offset == -1
    assert sample.consonant == -2
    assert sample.cutoff == -3
    assert sample.preutterance == -4
    assert sample.overlap == -5


def test_sample_wrong_param_type():
    with pytest.raises(ValueError):
        Sample.parse("a=b,c,d,e,f,g")


def test_sample_not_enough_params():
    with pytest.raises(ValueError):
        Sample.parse("a=b,")


def test_sample_non_property():
    with pytest.raises(ValueError):
        Sample.parse("[lol]")


def test_sample_slice():
    silence = Segment.silent(1000)

    # Sample looks like the following:
    # [----------]
    #  ^ ^       ^
    #  | |       |
    #  | |       cutoff (0)
    #  | consonant (200)
    #  offset (100)
    sample = Sample("", "", 100, 200, 0, 100, 0)

    consonant, vowel = sample.slice(silence)
    assert len(consonant) == 200
    assert len(vowel) == 700
