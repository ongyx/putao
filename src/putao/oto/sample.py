import dataclasses
from typing import Any, Self

from .. import audio, ini


@dataclasses.dataclass(frozen=True, slots=True)
class Sample:
    """A voice sample in a voicebank. All non-string values are in miliseconds.

    Attributes:
        file: The path to the sample's audio file relative to the voicebank's directory.

        alias: The name of the syllable the sample represents.

        offset: Region from the start of the sample to ignore.
            All other values are offsets from this unless specified otherwise
            (i.e., consonant region = sample[offset:offset + consonant]).

        consonant: Region where the sample is not stretched by the voice engine.
            This region not only contains the consonant, but also the front part of the vowel where the waveform has not stabilized yet.

        cutoff: Region from the end of the sample to ignore.
            If negative, the cutoff is interpreted relative to the offset instead.

        preutterance: Region where the sample should play before the actual note starts.
            This is usually in the middle of the consonant region where the sample transitions from the consonant to the vowel.

        overlap: Region where the previous note's vowel fades out.
    """

    file: str
    alias: str
    offset: float
    consonant: float
    cutoff: float
    preutterance: float
    overlap: float

    def slice(self, segment: audio.Segment) -> tuple[audio.Segment, audio.Segment]:
        """Slice an audio segment into a consonant and vowel.

        Args:
            segment: The audio segment to slice.

        Returns:
            A tuple of the consonant and vowel regions.
        """

        cutoff = self.cutoff
        if cutoff > 0:
            cutoff += self.offset

        syllable = segment[self.offset : cutoff]

        return syllable[: self.consonant], syllable[self.consonant :]

    @classmethod
    def parse(cls, entry: str) -> Self:
        """Parse a sample entry in an oto.ini file.

        Args:
            entry: The sample entry.

        Returns:
            The parsed sample.

        Raises:
            ValueError: The config could not be parsed.
        """

        config = ini.parse(entry)
        if not isinstance(config, ini.Property):
            raise ValueError(f"sample entry is invalid: '{entry}'")

        file = config.key
        alias, *params = config.value.split(",")

        return cls(
            file=file,
            alias=alias,
            # These parameters must be converted to float.
            **{
                k: float(v)
                for k, v in zip(
                    ["offset", "consonant", "cutoff", "preutterance", "overlap"], params
                )
            },
        )
