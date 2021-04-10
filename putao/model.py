# coding: utf8
"""This module models elements from UTAU, hence the name."""

import abc
import functools
import logging
import pathlib
from dataclasses import dataclass
from typing import Optional, Tuple, Union

import librosa
import numpy as np
import pyrubberband as pyrb
import pyworld
import soundfile
from pydub import AudioSegment

from . import utau, utils

# disable numpy pickle load/dump (we don't use object arrays).
np.save = functools.partial(np.save, allow_pickle=False)
np.load = functools.partial(np.load, allow_pickle=False)

_log = logging.getLogger("putao")


# Notes are the combination of a phenome, duration and pitch.
@dataclass
class _NoteBase:
    duration: int

    def dump(self) -> dict:
        return {**self.__dict__.copy(), "type": self.__class__.__name__.lower()}


@dataclass
class Note(_NoteBase):
    pitch: int
    entry: utau.Entry

    def dump(self):
        dump = {k: v for k, v in super().dump().items() if k != "entry"}
        dump["phoneme"] = self.entry.alias

        return dump


@dataclass
class Rest(_NoteBase):
    pass


class Resampler(abc.ABC):
    """A resampler pitches and streches phonemes to render a note.

    Args:
        voicebank: The voicebank to render with.

    Attributes:
        voicebank: See args.
    """

    def __init__(self, voicebank: utau.Voicebank):
        self.voicebank = voicebank

    @property
    def name(self):
        return self.__class__.__name__

    def slice(
        self, audio: AudioSegment, entry: utau.Entry
    ) -> Tuple[AudioSegment, AudioSegment, int]:
        """Slice the consonant and vowel out of a phenome wavfile.

        The audio segments are converted to stereo at 44.1kHz.

        Args:
            audio: The phenome wavfile as an audio segment.
            entry: The voicebank entry for the phenome.

        Returns:
            A three-tuple of (consonant, vowel, total_duration).
        """

        audio = audio.set_frame_rate(utils.SAMPLE_RATE).set_channels(2)

        # calculate milisecond offsets for the consonant and vowel.
        c_start = entry.offset
        c_end = c_start + entry.consonant
        consonant = audio[c_start:c_end]

        v_start = c_end
        v_end = len(audio) - entry.cutoff
        vowel = audio[v_start:v_end]

        duration = len(consonant) + len(vowel)

        return consonant, vowel, duration

    @abc.abstractmethod
    def pitch(self, note: Note) -> AudioSegment:
        """Pitch the consonant and vowel.

        Args:
            note: The note to pitch.

        Returns:
            The pitched note's wavfile, as an audio segment.
        """

    @abc.abstractmethod
    def stretch(self, vowel: AudioSegment, ratio: float) -> AudioSegment:
        """Stretch the vowel according to ratio.

        Args:
            vowel: The vowel to stretch.
            ratio: How long to stretch the vowel (duration divided by stretched duration).

        Returns:
            The stretched vowel.
        """

    def render(
        self, note: Union[Note, Rest], next_note: Optional[Union[Note, Rest]] = None
    ) -> AudioSegment:
        """Render a note to an audio segment.

        Args:
            note: The note to render.
            next_note: The next note (after this one).
                The preutterace and overlap of the next note are required to
                correctly calculate how long to stretch the wavfile.

        Returns:
            The pitched and stretched audio segment.
        """
        if isinstance(note, Rest):
            return AudioSegment.silent(note.duration)

        audio = self.pitch(note)

        consonant, vowel, phoneme_duration = self.slice(audio, note.entry)

        actual_duration = note.entry.preutterance + note.duration

        if next_note is not None and isinstance(next_note, Note):
            actual_duration += next_note.entry.overlap - next_note.entry.preutterance

        if actual_duration < phoneme_duration:
            # just cut off the end of the phoneme
            render = (consonant + vowel)[: note.duration]

        else:
            # calculate how much time will be used to loop the vowel.
            vowel_loop_dur = actual_duration - len(consonant)

            # vowel_loop = AudioSegment.silent(vowel_loop_dur).overlay(vowel, loop=True)
            # stretch instead, looping causes clicking noises
            ratio = vowel_loop_dur / len(vowel)
            vowel_loop = self.stretch(vowel, ratio)

            render = consonant + vowel_loop

        return render

    @abc.abstractmethod
    def gen_frq(
        self, wavfile: pathlib.Path, force: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, ...]]:
        """Generate a .frq file (or the file(s) that this resampler uses) to speed up rendering.

        Args:
            wavfile: The wavfile to generate a .frq file for.
                The parent folder is the voicebank.
            force: Whether or not to generate the frq if it already has been.
                Defaults to False.

        Returns:
            The generated frq file, as a tuple of numpy arrays.
        """

    def gen_frq_all(self, force: bool = False):
        """Generate .frq files for all wavfiles in a voicebank.

        Args:
            force: Same meaning as in .gen_frq().
        """

        total = len(self.voicebank.wavfiles)
        for count, wavfile in enumerate(self.voicebank.wavfiles, start=1):
            _log.debug(f"[resampler] generating frq {count} of {total} ({wavfile})")
            self.gen_frq(wavfile, force=force)


class WorldResampler(Resampler):

    # this file is stored in native NumPy format.
    # **NOT** compatible with other resamplers!
    FRQ = ".world.npz"

    def gen_frq(self, wavfile, force=False):

        frq_path = wavfile.with_suffix(self.FRQ)

        if not frq_path.is_file() or force:

            wav, srate = soundfile.read(wavfile)
            f0, sp, ap = pyworld.wav2world(wav, srate)

            if not f0.nonzero()[0].size:
                raise RuntimeError(f"f0 estimation failed for {wavfile}!!!")

            np.savez(frq_path, **{"f0": f0, "sp": sp, "ap": ap})

        else:
            frq = np.load(frq_path)
            f0, sp, ap = [frq[n] for n in ("f0", "sp", "ap")]

        return f0, sp, ap

    def pitch(self, note):
        f0, sp, ap = self.gen_frq(note.entry.wav)
        sr = utils.srate(note.entry.wav)

        # estimate pitch
        # get rid of zero values, average will be much less accurate.
        hz = np.average(f0[f0.nonzero()])

        note_hz = utils.Pitch(semitone=note.pitch).hz

        # add the difference
        f0[f0.nonzero()] += note_hz - hz

        # FIXME: some singing noises are grazed
        # i.e _い.wav (in teto voicebank).
        # https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder/issues/61
        arr = pyworld.synthesize(f0, sp, ap, sr)
        seg = utils.arr2seg(arr, sr)
        return seg

    def stretch(self, vowel, ratio):
        x = utils.seg2arr(vowel)
        fs = vowel.frame_rate
        # time stretching fails??
        y = pyrb.time_stretch(x, fs, ratio)
        return utils.arr2seg(y, fs)


class RosaResampler(Resampler):

    FRQ = ".rosa.npy"

    def gen_frq(self, wavfile, force=False):
        frq_path = wavfile.with_suffix(self.FRQ)

        if not frq_path.is_file() or force:

            wav, srate = soundfile.read(wavfile)

            # FIXME: pitch detection not working well
            f0, _, _ = librosa.pyin(
                wav.T,
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
                sr=srate,
            )

            np.save(frq_path, f0)

        else:
            f0 = np.load(frq_path)

        return f0

    def pitch(self, note):
        f0 = self.gen_frq(note.entry.wav)
        wav, srate = soundfile.read(note.entry.wav)

        hz = np.nanmean(f0)
        semitones = utils.Pitch(hz=hz)._semitone

        return utils.arr2seg(
            pyrb.pitch_shift(wav, srate, note.pitch - semitones), srate
        )

    def stretch(self, vowel, ratio):
        return WorldResampler.stretch(self, vowel, ratio)


# nicer way of retreving resamplers.
RESAMPLERS = {cls.__name__: cls for cls in Resampler.__subclasses__()}
