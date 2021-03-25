# coding: utf8

import textwrap

import pytest

from putao.backend import mmlx


TEST_SCRIPTS = {
    textwrap.dedent(
        """
    l8

    @lead
    |na ga re te ku
    def16g16a
    """
    ): 8,
    textwrap.dedent(
        """
    cdefgab
    pr
    o4
    <>
    l8
    t240

    # a comment
    """
    ): 14,
}


def test_parser():
    for script, token_count in TEST_SCRIPTS.items():

        parsed = mmlx.Parser.parseString(script)
        print(parsed)
        assert len(parsed) == token_count


def test_interpreter():
    itpr = mmlx.Interpreter(list(TEST_SCRIPTS)[0])
    print(itpr.execute())


def test_not_enough_lyrics():
    itpr = mmlx.Interpreter(
        textwrap.dedent(
            """
            |a e i o u
            cdefgab
            """
        )
    )

    with pytest.raises(ValueError):
        itpr.execute()
