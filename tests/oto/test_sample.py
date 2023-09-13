import pytest

from putao.oto import ini, Sample


def test_sample():
    sample = Sample.parse(ini.parse("あ.wav=あ,1,2,3,4,5"))
    assert sample.file == "あ.wav"
    assert sample.alias == "あ"
    assert sample.offset == 1
    assert sample.consonant == 2
    assert sample.cutoff == 3
    assert sample.preutterance == 4
    assert sample.overlap == 5


def test_sample_wrong_param_type():
    with pytest.raises(ValueError):
        Sample.parse(ini.parse("a=b,c,d,e,f,g"))


def test_sample_not_enough_params():
    with pytest.raises(ValueError):
        Sample.parse(ini.parse("a=b,"))


def test_sample_non_property():
    with pytest.raises(ValueError):
        Sample.parse(ini.parse("[lol]"))