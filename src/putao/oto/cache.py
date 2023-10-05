import collections
from typing import Iterator


from .. import audio

from .sample import Sample
from .voicebank import Voicebank


class Cache(collections.UserDict[str, audio.Segment]):
    """A sample cache backed by a voicebank.
    Samples are loaded only as needed.

    Attributes:
        voicebank: The voicebank to load samples from.
    """

    voicebank: Voicebank

    def __init__(self, voicebank: Voicebank):
        self.voicebank = voicebank

        super().__init__()

    def get(self, sample: Sample) -> audio.Segment | None:
        """Load the sample's audio as a segment.
        If the sample has already been loaded, the existing audio is returned.

        Note that only the audio after the sample's offset is loaded.

        Args:
            sample: The sample's alias.

        Returns:
            The sample's audio or None if the sample does not exist.
        """

        if sample.alias not in self:
            # Try to load the sample's audio.
            try:
                segment = audio.Segment.from_file(self.voicebank.path_to(sample))
            except (KeyError, FileNotFoundError):
                return None
            else:
                self[sample.alias] = segment[sample.offset :]

        return self[sample.alias]
