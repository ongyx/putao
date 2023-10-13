from typing import Self

import librosa.effects

from .. import audio, oto, ust

from .base import Wavtool


class Librosa:
    """Wavtool implementation based on librosa.effects."""

    vb: oto.Voicebank
    song: ust.Song

    def __init__(self, vb: oto.Voicebank, song: ust.Song, **config):
        self.vb = vb
        self.song = song

    def stretch(self, note: ust.Note, seg: audio.Segment) -> audio.Segment:
        samp = self.vb[note.lyric]
        duration = note.duration(self.song.settings.tempo)

        consonant, vowel = samp.slice(seg)
        rate = (duration - len(consonant)) / len(vowel)

        vowel = vowel.spawn(librosa.effects.time_stretch(vowel.array, rate=rate))

        return consonant + vowel


_: type[Wavtool] = Librosa
