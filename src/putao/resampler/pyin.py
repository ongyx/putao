from typing import Self

import librosa

from .. import audio, oto, ust

from .base import Resampler


class pYIN:
    """Resampler implementation based on librosa and the pYIN algorithm."""

    vb: oto.Voicebank
    song: ust.Song

    # Map of sample to (audio, f0).
    cache: dict[oto.Sample, float]

    def __init__(self, vb: oto.Voicebank, song: ust.Song, **config):
        self.vb = vb
        self.song = song

        self.cache = {}

        # Get the F0 for each voice sample in the voicebank.
        for samp in vb:
            seg = vb.open(samp)

            try:
                with vb.path_to_frq(samp).open("rb") as f:
                    frq = oto.Frq.load(f)

            except FileNotFoundError:
                f0, _, _ = librosa.pyin(
                    seg.array, fmin=55, fmax=1000, sr=seg.srate, frame_length=256
                )

                frq = oto.Frq(f0)

                with vb.path_to_frq(samp).open("wb") as f:
                    frq.dump(f)

            self.cache[samp] = frq.average

    def pitch(self, note: ust.Note, seg: audio.Segment) -> audio.Segment:
        samp = self.vb[note.lyric]
        f0 = self.cache[samp]

        # Calculate the semitone steps between the target MIDI note and the F0.
        steps = note.notenum - oto.Pitch(f0).midi

        return seg.spawn(
            librosa.effects.pitch_shift(seg.array, sr=seg.srate, n_steps=steps)
        )


_: type[Resampler] = pYIN
