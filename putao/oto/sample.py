import dataclasses
from typing import Any, Self

from . import ini


@dataclasses.dataclass
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
    """

    file: str
    alias: str
    offset: int
    consonant: int
    cutoff: int
    preutterance: int
    overlap: int

    @classmethod
    def parse(cls, cfg: ini.Config) -> Self:
        """Parse a sample config in an oto.ini file.

        Args:
            cfg: The sample config.

        Returns:
            The parsed sample entry.

        Raises:
            ValueError: The config could not be parsed.
            IndexError: There are not enough parameters.
        """

        kwargs: dict[str, Any] = {}

        if not isinstance(cfg, ini.Property):
            raise ValueError("config is not an ini property")

        kwargs["file"] = cfg.key

        params = cfg.value.split(",")

        # First parameter is the sample's alias.
        kwargs["alias"] = params[0]

        # The rest of the parameters must be converted to int.
        for i, p in enumerate(
            ["offset", "consonant", "cutoff", "preutterance", "overlap"],
            start=1,
        ):
            kwargs[p] = int(params[i])

        return cls(**kwargs)
