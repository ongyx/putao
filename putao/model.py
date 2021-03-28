# coding: utf8
"""This module models elements from UTAU, hence the name."""

import abc
import functools
import io
from dataclasses import dataclass
from typing import Optional, Tuple, Union

import numpy as np
import pyworld
import soundfile
from pydub import AudioSegment

from . import utau


# disable numpy pickle load/dump (we don't use object arrays).
np.save = functools.partial(np.save, allow_pickle=False)
np.load = functools.partial(np.load, allow_pickle=False)


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

    @abc.abstractmethod
    def gen_frq(self):
        """Generate .frq files (or the files that this resampler uses) to speed up rendering.

        Args:
            voicebank: The voicebank to generate .frq files for.
        """

    @abc.abstractmethod
    def load_frq(self, entry: utau.Entry) -> Tuple[np.ndarray, ...]:
        """Load previously generated .frq files.

        Args:
            entry: The voicebank entry to load the .frq file(s) for.

        Returns:
            A variable-length tuple of numpy arrays.
        """

    def slice(
        self, audio: AudioSegment, entry: utau.Entry
    ) -> Tuple[AudioSegment, AudioSegment, int]:
        """Slice the consonant and vowel out of a phenome wavfile.

        Args:
            audio: The phenome wavfile as an audio segment.
            entry: The voicebank entry for the phenome.

        Returns:
            A three-tuple of (consonant, vowel, total_duration).
        """

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


class WorldResampler(Resampler):

    # these files are stored in native NumPy format.
    # **NOT** compatible with other resamplers!
    FRQS = (".dio.npy", ".star.npy", ".platinum.npy")

    def gen_frq(self, voicebank):
        for wavfile in voicebank.wavfiles:

            wav, srate = soundfile.read(wavfile)
            f0, sp, ap = pyworld.wav2world(wav, srate)

            for ext, array in zip(self.FRQS, (f0, sp, ap)):
                np.save(wavfile.with_suffix(ext), array)

    def load_frq(self, entry):
        frqs = []

        for ext in self.FRQS:
            array = np.load(entry.wav.with_suffix(ext))
            frqs.append(array)

        return tuple(frqs)

    def _pitch(self, note):
        f0, sp, ap = self.load_frq(note.entry)

    def render(self, note, next_note=None):
        if isinstance(note, Rest):
            return AudioSegment.silent(note.duration)

        audio = AudioSegment.from_file(note.entry.wav)

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
            vowel_loop = AudioSegment.silent(vowel_loop_dur).overlay(vowel, loop=True)

            render = consonant + vowel_loop

        return render
