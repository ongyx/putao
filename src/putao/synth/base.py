from typing import Protocol

from .. import audio, oto, ust


class Synth(Protocol):
    """A tool for pitch-shifting and time-stretching, equivalent to UTAU's resampler and wavtool respectively."""

    def setup(self, vb: oto.Voicebank, song: ust.Song):
        """Setup the synth with parameters from the voicebank and/or song.

        Args:
            song: The UST song.
            vb: The voicebank to synthesize with.
        """

        ...

    def synthesize(self, note: ust.Note) -> audio.Segment:
        """Synthesize a note's voice sample to an audio segment.

        Generally, synthesis consists of three steps:
        * Pitching - the voice sample is tuned to the note's MIDI value.
        * Stretching - the voice sample is split into a consonant and vowel, and the vowel is stretched/repeated to the note's length.
        * Joining - the consonant and vowel is concatenated.

        Implementations must be thread-safe.

        Args:
            note: The UST note.
        """
        ...

    def teardown(self):
        """Teardown the synth and perform cleanup if needed."""
        ...
