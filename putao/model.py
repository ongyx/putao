# coding: utf8
"""This module models elements from UTAU, hence the name."""

from dataclasses import dataclass
from typing import Optional, Union

from pydub import AudioSegment

from . import utau


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


class Resampler:
    """A resampler pitches and streches phonemes to render a note."""

    def __init__(self):
        pass

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

        audio = AudioSegment.from_file(note.entry.wav)

        # calculate milisecond offsets for the consonant and vowel.
        c_start = note.entry.offset
        c_end = c_start + note.entry.consonant
        consonant = audio[c_start:c_end]

        v_start = c_end
        v_end = len(audio) - note.entry.cutoff
        vowel = audio[v_start:v_end]

        phoneme_duration = len(consonant) + len(vowel)

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
