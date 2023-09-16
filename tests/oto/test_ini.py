import io

import pytest

from putao.oto import ini


def test_ini_section():
    cfg = ini.parse("[this is a section]")
    assert isinstance(cfg, ini.Section)
    assert cfg.name == "this is a section"


def test_ini_property():
    cfg = ini.parse("こんにちは=konnichiwa")
    assert isinstance(cfg, ini.Property)
    assert cfg.key == "こんにちは"
    assert cfg.value == "konnichiwa"


def test_ini_property_with_spaces():
    cfg = ini.parse("key = value")
    assert isinstance(cfg, ini.Property)
    assert cfg.key == "key"
    assert cfg.value == "value"


def test_ini_invalid():
    assert ini.parse("[hanging bracket") is None

    assert ini.parse("=empty property key") is None
