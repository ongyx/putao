import pathlib

from putao.oto import ini

from .sample import Sample

CONFIG_FILE = "oto.ini"


class Voicebank:
    """A collection of voice samples.

    Attributes:
        dir: The directory where the samples reside.
            oto.ini must be present inside the directory.
        samples: A mapping of sample aliases to the sample itself.

    Args:
        encoding: The encoding to read the oto.ini file with. Defaults to Shift-JIS.
    """

    dir: pathlib.Path
    samples: dict[str, Sample]

    def __init__(self, dir: pathlib.Path, encoding: str = "shift_jis"):
        self.dir = dir

        with (dir / CONFIG_FILE).open(encoding=encoding) as f:
            # Parse each ini config into a sample and map them by alias.
            samples = (Sample.parse(c) for c in ini.parse_file(f))

            self.samples = {s.alias: s for s in samples}

    def path_to(self, sample: Sample) -> pathlib.Path:
        """Returns the absolute path to the sample's audio file.

        Args:
            sample: The sample to get the audio file path for.

        Returns:
            The absolute path.
        """
        return self.dir / sample.file

    def __getitem__(self, alias: str) -> Sample:
        return self.samples[alias]
