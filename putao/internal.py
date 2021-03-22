# coding: utf8
"""Any classes/functions here should NOT be used outside of putao.
This contains the low-level parts of the rendering engine, and may change at any time.

You have been warned.
"""

import abc

from pydub import AudioSegment

from putao import utils, voicebank


class NoteBase(abc.ABC):
    def __init__(self, duration: int):
        self.duration = duration

    @abc.abstractmethod
    def render(self, preutter: int, overlap: int, pitch: int) -> AudioSegment:
        return

    def dump(self) -> dict:
        return {"type": self.__class__.__name__.lower(), "duration": self.duration}


class Rest(NoteBase):
    def render(self, preutter, overlap, pitch):
        return AudioSegment.silent(self.duration - preutter + overlap)


class Note(NoteBase):
    def __init__(self, entry: voicebank.Entry, pitch: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry = entry
        self.pitch = pitch

    def render(self, preutter, overlap, pitch):
        audio = AudioSegment.from_file(self.entry.wav)

        c_start = self.entry.offset
        c_end = c_start + self.entry.consonant
        consonant = audio[c_start:c_end]

        v_start = c_end
        v_end = len(audio) - self.entry.cutoff
        vowel = audio[v_start:v_end]

        phoneme_duration = len(consonant) + len(vowel)
        # preutterances extend this note into the previous one
        actual_duration = self.duration + self.entry.preutterance

        if actual_duration < phoneme_duration:
            # just cut off the end of the phoneme
            render = (consonant + vowel)[: self.duration]

        else:
            # calculate how much time will be used to loop the vowel.
            vowel_loop_dur = actual_duration - len(consonant)
            vowel_loop = AudioSegment.silent(vowel_loop_dur).overlay(vowel, loop=True)

            render = consonant + vowel_loop

        return utils.pitch_shift(
            render[: len(render) - preutter + overlap], self.pitch - pitch
        )
