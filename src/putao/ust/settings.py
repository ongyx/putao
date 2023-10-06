from typing import Self

import attrs

from ._conv import converter


@attrs.define
class Settings:
    """A song's configuration.

    Attributes:
        tempo: The beats per minute.
        tracks: Number of tracks in the UST.
        projectname: Name of the song.
        voicedir: Path to the voicebank on disk.
        outfile: Where to write the rendered song to.
        cachedir: Where to store temporary samples.
        tool1: The wave file tool for time stretching.
        tool2: The resampler tool for pitch shifting.
        mode2: Whether or not to use mode 2 pitch bending.
        flags: Rendering flags for the song.
    """

    tempo: float
    tracks: int
    projectname: str
    voicedir: str
    outfile: str
    cachedir: str
    tool1: str
    tool2: str
    mode2: bool
    flags: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the settings to a dict.

        Returns:
            The dict.
        """

        return {k: str(v) for k, v in converter.unstructure(self).items()}

    @classmethod
    def from_dict(cls, config: dict[str, str]) -> Self:
        """Parse settings from a dict.

        Args:
            config: The dict to parse from.

        Returns:
            The settings.
        """

        return converter.structure(config, cls)
