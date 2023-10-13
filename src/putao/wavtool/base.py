from typing import Protocol

from .. import audio, oto, ust


class Wavtool(Protocol):
    """A tool for time-stretching the vowels of voice samples.

    Wavtools split a pitch-shifted voice sample into a consonant and vowel,
    then stretches or repeats the vowel to fit the length of a note.
    """

    def setup(self, vb: oto.Voicebank, song: ust.Song):
        """Setup the wavtool with parameters from the song and/or voicebank.

        Args:
            vb: The voicebank to load voice samples from.
            song: The UST song.
        """
        ...

    def stretch(self, note: ust.Note, seg: audio.Segment) -> audio.Segment:
        """Stretch the vowel of the voice sample in segment to fit the note length.

        Implementations must be thread-safe.

        Args:
            note: The UST note.
            segment: The voice sample.

        Returns:
            The stretched voice sample.
        """
        ...
