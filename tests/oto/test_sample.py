import pytest

from putao.oto import Sample


def test_sample():
    sample = Sample.parse("あ.wav=あ,1,2,3,4,5")

    assert sample is not None
    assert sample.file == "あ.wav"
    assert sample.alias == "あ"
    assert sample.offset == 1
    assert sample.consonant == 2
    assert sample.cutoff == 3
    assert sample.preutterance == 4
    assert sample.overlap == 5


def test_sample_wrong_param_type():
    assert Sample.parse("a=b,c,d,e,f,g") is None


def test_sample_not_enough_params():
    assert Sample.parse("a=b,") is None


def test_sample_non_property():
    assert Sample.parse("[lol]") is None
