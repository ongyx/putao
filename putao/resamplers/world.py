# coding: utf8

from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass

import numpy as np
import pyworld
import soundfile

from .. import model, utils

_log = logging.getLogger(__name__)

# this file is stored in native NumPy format.
# **NOT** compatible with other resamplers!
EXTENSION = ".world.npz"


@dataclass
class Frq:
    f0: np.ndarray
    sp: np.ndarray
    ap: np.ndarray

    @classmethod
    def load(cls, wavfile: str) -> Frq:
        path = pathlib.Path(wavfile).with_suffix(EXTENSION)

        if path.is_file():
            data = np.load(path)

        else:
            f0, sp, ap = pyworld.wav2world(*soundfile.read(wavfile))

            if not f0.nonzero()[0].size:
                raise RuntimeError(f"f0 estimation failed for {wavfile}!!!")

            data = {"f0": f0, "sp": sp, "ap": ap}

            np.savez(path, **data)

        return cls(**data)


class Resampler(model.Resampler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # frq files are lazily generated
        self.cache = {}

    def frq(self, wav):
        if wav not in self.cache:
            self.cache[wav] = Frq.load(wav)

        return self.cache[wav]

    def pitch(self, note):
        entry = self.voicebank[note.syllable]

        frq = self.frq(entry.wav)
        sr = utils.srate(entry.wav)

        # estimate pitch
        # get rid of zero values, average will be much less accurate.
        hz = np.average(frq.f0[frq.f0.nonzero()])

        note_hz = utils.Pitch(semitone=note.pitch).hz

        # add the difference
        frq.f0[frq.f0.nonzero()] += note_hz - hz

        _log.debug(f"pitching note ({note_hz}hz, semitone {note.pitch})")

        # FIXME: some singing noises are grazed
        # i.e _い.wav (in teto voicebank).
        # https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/issues/61
        arr = pyworld.synthesize(frq.f0, frq.sp, frq.ap, sr)
        seg = utils.arr2seg(arr, sr)
        return seg
