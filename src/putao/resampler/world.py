import dataclasses
import pathlib
from typing import Self

import numpy as np
import pyworld
from numpy.typing import NDArray

from .. import audio, oto, ust

from .base import Resampler

FRQ_EXT = ".world.npz"


@dataclasses.dataclass(slots=True)
class _Parameter:
    f0: NDArray[np.float64]
    sp: NDArray[np.float64]
    ap: NDArray[np.float64]

    f0_avg: np.float64 = dataclasses.field(init=False)

    def __post_init__(self):
        # Ignore zero values as the average F0 would be skewed otherwise.
        self.f0_avg = np.nanmean(self.f0)

    def write_to(self, file: pathlib.Path):
        np.savez_compressed(file, **dataclasses.asdict(self))

    @classmethod
    def read_from(cls, file: pathlib.Path):
        return cls(**np.load(file, allow_pickle=False))

    @classmethod
    def analyze(cls, seg: audio.Segment) -> Self:
        return cls(*pyworld.wav2world(seg.array, seg.srate))


class World:
    """Resampler implementation based on the WORLD algorithm."""

    vb: oto.Voicebank
    song: ust.Song

    # Map of sample to (segment, parameter).
    cache: dict[oto.Sample, tuple[audio.Segment, _Parameter]]

    def __init__(self, vb: oto.Voicebank, song: ust.Song, **config):
        self.vb = vb
        self.song = song

        self.cache = {}

        for samp in vb:
            seg = vb.open(samp)
            frq_path = vb.path_to_frq(samp).with_suffix(FRQ_EXT)

            try:
                param = _Parameter.read_from(frq_path)
            except FileNotFoundError:
                param = _Parameter.analyze(seg)
                param.write_to(frq_path)

            self.cache[samp] = (seg, param)

        return self

    def pitch(self, note: ust.Note) -> audio.Segment:
        samp = self.vb[note.lyric]
        seg, param = self.cache[samp]

        # Shift the F0 parameter by offset.
        offset = note.pitch - param.f0_avg

        return seg.spawn(
            pyworld.synthesize(param.f0 + offset, param.sp, param.ap, seg.srate)
        )


_: type[Resampler] = World
