import librosa

from .. import audio, oto, ust

from .base import Resampler


class pYIN:
    """Resampler implementation based on librosa and the pYIN algorithm."""

    f0: dict[oto.Sample, float]

    vb: oto.Voicebank
    song: ust.Song

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

    def pitch(self, note: ust.Note) -> audio.Segment:
        samp = self.vb[note.lyric]
        seg = self.vb.load(samp)

        f0 = self.f0[samp]
        # Calculate the semitone steps between the target MIDI note and the F0.
        steps = note.notenum - oto.Pitch(f0).midi

        return seg.spawn(
            librosa.effects.pitch_shift(seg.array, sr=seg.srate, n_steps=steps)
        )


_: type[Resampler] = pYIN
