# coding: utf8
"""Resampler base class."""

import abc
from typing import Union

from pydub import AudioSegment

from .. import utils, utau

from ..note import Note, Rest


class Resampler(abc.ABC):
    def __init__(self, voicebank: utau.Voicebank):
        self.voicebank = voicebank

    def render(self, note: Union[Note, Rest], next_note: Union[Note, Rest]):

        # pitch-shift first
        #        audio = utils.pitch_shift(
        #            *self.entry.load_frq(),
        #            self.pitch - pitch,
        #            utils._samplerate(self.entry.wav),
        #        )
        #        audio = audio.set_frame_rate(utils.SAMPLE_RATE)

        audio = AudioSegment.from_file(self.entry.wav)

        # calculate milisecond offsets for the consonant and vowel.
        c_start = self.entry.offset
        c_end = c_start + self.entry.consonant
        consonant = audio[c_start:c_end]

        v_start = c_end
        v_end = len(audio) - self.entry.cutoff
        vowel = audio[v_start:v_end]

        phoneme_duration = len(consonant) + len(vowel)

        actual_duration = self.entry.preutterance + self.duration + overlap - preutter

        if actual_duration < phoneme_duration:
            # just cut off the end of the phoneme
            render = (consonant + vowel)[: self.duration]

        else:
            # calculate how much time will be used to loop the vowel.
            vowel_loop_dur = actual_duration - len(consonant)
            vowel_loop = AudioSegment.silent(vowel_loop_dur).overlay(vowel, loop=True)

            render = consonant + vowel_loop

        return render
