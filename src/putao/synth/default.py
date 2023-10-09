import librosa
import librosa.effects

from putao.oto.frq import Frq
from putao.oto.sample import Sample

from .. import audio, oto, ust

from .base import Synth


class Default:
    """The default synth implementation based on librosa and pYIN."""

    vb: oto.Voicebank
    song: ust.Song

    f0: dict[Sample, float]

    def __init__(self):
        self.f0 = {}

    def setup(self, vb: oto.Voicebank, song: ust.Song):
        self.vb = vb
        self.song = song

        # Get the F0 for each voice sample in the voicebank.
        for samp in vb:
            try:
                frq = vb.load_frq(samp)
            except FileNotFoundError:
                seg = vb.load(samp)

                f0, _, _ = librosa.pyin(
                    seg.array, fmin=55, fmax=1000, sr=seg.srate, frame_length=256
                )

                frq = oto.Frq(f0)

                with vb.path_to_frq(samp).open("wb") as f:
                    frq.dump(f)

            self.f0[samp] = frq.average

    def synthesize(self, note: ust.Note) -> audio.Segment:
        duration = note.duration(self.song.settings.tempo)

        # Bail - note is a rest!
        if note.is_rest():
            return audio.Segment.silent(duration)

        samp = self.vb[note.lyric]
        seg = self.vb.load(samp)

        f0 = self.f0[samp]
        # Calculate the semitone steps between the target MIDI note and the F0.
        steps = note.notenum - oto.Pitch(f0).midi

        seg = seg.spawn(
            librosa.effects.pitch_shift(seg.array, sr=seg.srate, n_steps=steps)
        )

        consonant, vowel = samp.slice(seg)
        rate = (duration - len(consonant)) / len(vowel)

        vowel = vowel.spawn(librosa.effects.time_stretch(vowel.array, rate=rate))

        return consonant + vowel

    def teardown(self):
        self.vb.load.cache_clear()
        self.vb.load_frq.cache_clear()


# Sanity check to make sure we actually implement Synth.
_: type[Synth] = Default
