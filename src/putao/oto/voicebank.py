import io
import pathlib

import chardet

from putao.oto import ini

from .sample import Sample

CONFIG_FILE = "oto.ini"


class Voicebank:
    """A collection of voice samples.

    Attributes:
        dir: The directory where the samples reside.
            An oto.ini file must be present inside the directory.
        config: The path to the oto.ini file.
        samples: A mapping of sample aliases to the sample itself.
        encoding: The file encoding detected from the oto.ini.
    """

    dir: pathlib.Path
    config: pathlib.Path
    samples: dict[str, Sample]
    encoding: str

    def __init__(self, dir: str | pathlib.Path):
        if isinstance(dir, str):
            dir = pathlib.Path(dir)

        self.dir = dir
        self.config = dir / CONFIG_FILE

        with self.config.open("rb") as f:
            buffer = f.read()

        encoding = chardet.detect(buffer)["encoding"]
        if encoding is None:
            raise ValueError(f"encoding detection failed for {self.config}")

        self.encoding = encoding

        with io.StringIO(buffer.decode(encoding)) as f:
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
