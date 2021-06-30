# coding: utf8
"""This module models elements from UTAU, hence the name."""

import abc
import logging
from typing import Optional, Tuple

import pyrubberband as pyrb
from pydub import AudioSegment

from . import utau, utils
from .jsonclasses import dataclass

_log = logging.getLogger("putao")


@dataclass
class Note:
    """Notes are the combination of a duration, pitch and syllable."""

    duration: int
    pitch: int
    syllable: str


@dataclass
class Rest(Note):
    def __init__(self, *args, **kwargs):
        kwargs["pitch"] = -1
        kwargs["syllable"] = ""
        super().__init__(*args, **kwargs)


class Resampler(abc.ABC):
    """A resampler renders notes by pitching and streching samples.
    Effects may also be applied (i.e portomento).

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

    @abc.abstractmethod
    def pitch(self, note: Note) -> AudioSegment:
        """Pitch the note.

        Args:
            note: The note to pitch.

        Returns:
            An AudioSegment of the pitched note.
        """

    def slice(
        self, note: Note, audio: AudioSegment
    ) -> Tuple[AudioSegment, AudioSegment]:
        """Slice a note's render into its consonant and vowel.

        Args:
            note: The note.
            audio: The render.

        Returns:
            A two-tuple of (consonant, vowel) as AudioSegments.

        Raises:
            ValueError, if this note is a Rest.
        """

        if not note.syllable:
            raise ValueError("note is a rest")

        entry = self.voicebank[note.syllable]

        # calculate milisecond offsets for the consonant and vowel.
        c_start = entry.offset
        c_end = c_start + entry.consonant
        consonant = audio[c_start:c_end]

        v_start = c_end
        v_end = len(audio) - entry.cutoff
        vowel = audio[v_start:v_end]

        return consonant, vowel

    def stretch(
        self, consonant: AudioSegment, vowel: AudioSegment, duration: int
    ) -> AudioSegment:
        """Stretch a note by looping/stretching the vowel.

        Args:
            consonant: The consonant part of the note.
            vowel: The vowel part of the note.
            duration: The total duration the note should be stretched to.

        Returns:
            The consonant and stretched/looped vowel as a joined AudioSegment.
        """

        actual_duration = len(consonant) + len(vowel)

        if duration < actual_duration:
            # Very short note, just cut off
            render = (consonant + vowel)[:duration]

        else:
            # stretch vowel
            # TODO: enable option for looping?
            ratio = (actual_duration - len(consonant)) / len(vowel)

            # convert to numpy array and back
            x = utils.seg2arr(vowel)
            sr = vowel.frame_rate

            y = pyrb.time_stretch(x, sr, ratio)

            render = consonant + utils.arr2seg(y, sr)

        return render

    def render(self, note: Note, next_note: Optional[Note]) -> AudioSegment:
        """Render a note.
        The note is pitched, then sliced and stretched to create the render.

        Args:
            note: The note to render.
            next_note: The next note after the one to render.
                This is needed to correctly stretch/shorten the note.
                If there are no notes after this, None should be passed.
        """

        if not note.syllable:
            render = AudioSegment.silent(note.duration)

        else:
            entry = self.voicebank[note.syllable]

            consonant, vowel = self.slice(note, self.pitch(note))

            duration = entry.preutterance + note.duration

            if isinstance(next_note, Note):
                next_entry = self.voicebank[next_note.syllable]
                duration += next_entry.overlap - next_entry.preutterance

            render = self.stretch(consonant, vowel, duration)

        return render
