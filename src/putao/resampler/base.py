from typing import Protocol

from .. import audio, oto, ust


class Resampler(Protocol):
    """A tool for pitch-shifting voice samples.

    Resamplers essentially make an UTAUloid sing by virtue of:
    * Determining the fundamental frequency (F0) of a voice sample.
    * Shifting the F0 of the voice sample to hit a note.
    * Applying ADSR envelopes and filters.
    """

    def setup(self, vb: oto.Voicebank, song: ust.Song):
        """Setup the resampler with parameters from the song and/or voicebank.

        Args:
            vb: The voicebank to load voice samples from.
            song: The UST song.
        """
        ...

    def pitch(self, note: ust.Note) -> audio.Segment:
        """Load the voice sample of note and pitch-shift it to the note's MIDI value.

        Implementations must be thread-safe.

        Args:
            note: The UST note.

        Returns:
            The pitch-shifted voice sample.
        """
        ...
