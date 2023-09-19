import dataclasses
import re
from typing import Any, Self

REGEX = re.compile(
    r"""
    # Anchor to the start of the line.
    ^

    # Match the sample entry (Whitespace around the equals sign is ignored).
    (?P<file>.+?) =
        (?P<alias>.+?) ,
        (?P<offset>\d+) ,
        (?P<consonant>\d+) ,
        (?P<cutoff>\d+) ,
        (?P<preutterance>\d+) ,
        (?P<overlap>\d+)

    # Anchor to the end of the line.
    $
    """,
    re.VERBOSE,
)


@dataclasses.dataclass(slots=True)
class Sample:
    """A voice sample in a voicebank. All int values are in miliseconds.

    Attributes:
        file: The path to the sample's audio file relative to the voicebank's directory.

        alias: The name of the syllable the sample represents.

        offset: Region from the start of the sample to ignore.
            All other values are offsets from this unless specified otherwise
            (i.e., consonant region = sample[offset:consonant]).

        consonant: Region where the sample is not stretched by the voice engine.
            This region not only contains the consonant, but also the front part of the vowel where the waveform has not stabilized yet.

        cutoff: Region from the end of the sample to ignore.

        preutterance: Where the note starts playing from.
            This is usually in the middle of the consonant region where the sample transitions from the consonant to the vowel.

        overlap: Where the previous note's vowel fades out.
    """

    file: str
    alias: str
    offset: int
    consonant: int
    cutoff: int
    preutterance: int
    overlap: int

    @classmethod
    def parse(cls, entry: str) -> Self | None:
        """Parse a sample entry in an oto.ini file.

        Args:
            entry: The sample entry.

        Returns:
            The parsed sample.

        Raises:
            ValueError: The config could not be parsed.
        """

        if match := REGEX.match(entry):
            kwargs: dict[str, Any] = match.groupdict()

            # These parameters must be converted to int.
            for p in ["offset", "consonant", "cutoff", "preutterance", "overlap"]:
                kwargs[p] = int(kwargs[p])

            return cls(**kwargs)

        return None
