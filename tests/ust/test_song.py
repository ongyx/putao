import textwrap

import pytest

from putao.ust import Song


def test_song():
    song = Song.from_str(
        textwrap.dedent(
            """
            [#VERSION]
            UST Version1.2
            [#SETTING]
            tempo=120
            tracks=1
            projectname=「こんにちは、世界！」
            voicedir=./voicebanks/tougou
            outfile=konnichiwa_sekai.wav
            cachedir=konnichiwa_sekai.cache
            tool1=wavtool.exe
            tool2=resampler.exe
            mode2=true
            [#0000]
            length=120
            lyric=あ
            notenum=60
            preutterance=
            """
        )
    )

    assert song.version == "1.2"
    assert song.settings
    assert song.notes
