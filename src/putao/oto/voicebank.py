import io
import pathlib

from .sample import Sample

CONFIG_FILE = "oto.ini"


class Voicebank:
    """A collection of voice samples.

    A typical UTAU voicebank contains an `oto.ini` configuration file,
    any number of waveform voice samples (`.wav`), and frequnecy maps (`.frq`) for those samples.

    Voicebanks may be encoded in UTF-8 or Shift-JIS,
    but filenames may be mojibaked as code page 437 when extracted from a zip file on a non-Shift-JIS locale.

    Attributes:
        dir: The directory where the samples reside.
            An oto.ini file must be present inside the directory.
        config: The path to the oto.ini file.
        samples: A mapping of sample aliases to the sample itself.
        encoding: The file encoding detected from the oto.ini.
            If encoding is None, encoding detection is attempted.
    """

    dir: pathlib.Path
    config: pathlib.Path
    samples: dict[str, Sample]
    encoding: str

    def __init__(self, dir: str | pathlib.Path, encoding: str | None = None):
        if isinstance(dir, str):
            dir = pathlib.Path(dir)

        self.dir = dir
        self.config = dir / CONFIG_FILE

        with self.config.open("rb") as f:
            encoding = encoding or detect_encoding(f.readline())
            if encoding is None:
                raise ValueError(f"encoding detection failed for {self.config}")

            self.encoding = encoding

            f.seek(0)

            # Parse each ini config into a sample and map them by alias.
            # NOTE: The RE end-of-line anchor can't match CRLF newlines, hence the need for rstrip().
            samples = (Sample.parse(line.decode(encoding).rstrip()) for line in f)

            self.samples = {s.alias: s for s in samples if s}

    def path_to(self, sample: Sample) -> pathlib.Path:
        """Returns the absolute path to the sample's audio file.

        Args:
            sample: The sample to get the audio file path for.

        Returns:
            The absolute path.
        """

        if self.encoding != "utf_8":
            # A typical UTAU voicebank is encoded in Shift-JIS,
            # so file names end up mojibaked when zipped and extracted.
            # This is due to filenames being encoded as Shift-JIS and decoded as code page 437
            # which is the historical encoding used for zip files.
            #
            # Therefore the file name has to be purposely mojibaked to get the actual path.
            return self.dir / sample.file.encode(self.encoding).decode("cp437")

        return self.dir / sample.file

    def __getitem__(self, alias: str) -> Sample:
        return self.samples[alias]


def detect_encoding(
    data: bytes, encodings: list[str] = ["shift_jis", "utf_8"]
) -> str | None:
    """Attempt to detect the encoding of data.

    Args:
        text: The text to detect the encoding of.
        encodings: A list of possible encodings.

    Returns:
        The encoding if detection was successful, otherwise None.
    """

    for encoding in encodings:
        try:
            data.decode(encoding)
        except UnicodeDecodeError:
            continue
        else:
            return encoding

    return None
