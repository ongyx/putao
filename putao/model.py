# coding: utf8
"""This module models elements from UTAU, hence the name."""

import abc
import logging
from typing import Tuple

from pydub import AudioSegment, effects  # noqa

from . import utau
from .jsonclasses import dataclass

_log = logging.getLogger("putao")


@dataclass
class Note:
    """Notes are the combination of a duration, pitch and syllable."""

    duration: int
    pitch: int
    syllable: str

    def is_rest(self) -> bool:
        return self.pitch == 0 and not self.syllable

    def entry(self, vb: utau.Voicebank) -> utau.Entry:
        return vb[self.syllable]


@dataclass
class Rest(Note):
    def __init__(self, *args, **kwargs):
        kwargs["pitch"] = 0
        kwargs["syllable"] = ""
        super().__init__(*args, **kwargs)


class Resampler(abc.ABC):
    """A resampler renders notes by pitching and stretching samples.
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
        The length of the note should not change.

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

        entry = note.entry(self.voicebank)

        # calculate milisecond offsets for the consonant and vowel.
        c_start = entry.offset
        c_end = c_start + entry.consonant
        consonant = audio[c_start:c_end]

        v_start = c_end

        if entry.cutoff < 0:
            # negative cutoffs are measured from the offset onwards
            v_end = entry.offset + abs(entry.cutoff)
        else:
            v_end = len(audio) - entry.cutoff

        if v_end <= v_start:
            raise ValueError("vowel length is negative or zero")

        vowel = audio[v_start:v_end]

        return consonant, vowel

    def stretch(
        self, consonant: AudioSegment, vowel: AudioSegment, note: Note
    ) -> AudioSegment:
        """Stretch a note by looping/stretching the vowel.

        Args:
            consonant: The consonant segment of the note.
            vowel: The vowel segment of the note.
            note: The note itself.

        Returns:
            The consonant and stretched/looped vowel as a joined AudioSegment.
        """

        entry = note.entry(self.voicebank)

        duration = entry.preutterance + note.duration
        actual_duration = len(consonant) + len(vowel)

        if duration < actual_duration:
            # Very short note, just cut off
            render = (consonant + vowel)[:duration]

        else:
            # stretch vowel
            # TODO: enable option for looping?
            vowel_stretch = vowel.speedup(
                len(vowel) / (actual_duration - len(consonant))
            )
            render = consonant + vowel_stretch

        return render

    def render(self, note: Note) -> AudioSegment:
        """Render a note.
        The note is pitched, then sliced and stretched to create the render.

        Args:
            note: The note to render.

        Returns:
            The rendered note.
        """

        if note.is_rest():
            return AudioSegment.silent(note.duration)

        consonant, vowel = self.slice(note, self.pitch(note))
        return self.stretch(consonant, vowel, note)
