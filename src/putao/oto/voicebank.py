import io
import pathlib
import shutil
import zipfile
from collections.abc import Iterator
from typing import IO

import chardet

from .sample import Sample

CONFIG_FILE = "oto.ini"


class Voicebank:
    """A collection of voice samples.

    A typical UTAU voicebank contains an `oto.ini` configuration file,
    any number of waveform voice samples (`.wav`), and frequnecy maps (`.frq`) for those samples.

    Attributes:
        dir: The directory where the samples reside.
            An oto.ini file must be present inside the directory.
        config: The path to the oto.ini file.
        samples: A mapping of sample aliases to the sample itself.
        encoding: The file encoding of the oto.ini.
            If None, encoding detection is attempted.
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

        if encoding is None:
            # Attempt to detect the encoding.
            with self.config.open("rb") as f:
                encoding = detect_encoding(f)

            if encoding is None:
                raise ValueError(f"failed to detect encoding for {self.config}")

        self.encoding = encoding

        with self.config.open(encoding=encoding) as f:
            f.seek(0)

            # Parse each ini config into a sample and map them by alias.
            # NOTE: The RE end-of-line anchor can't match CRLF newlines, hence the need for rstrip().
            samples = (Sample.parse(line) for line in f)

            self.samples = {s.alias: s for s in samples if s}

    def path_to(self, sample: Sample) -> pathlib.Path:
        """Return the absolute path to the sample's audio file.

        Args:
            sample: The sample to get the audio file path for.

        Returns:
            The absolute path.
        """

        return self.dir / sample.file

    def path_to_frq(self, sample: Sample) -> pathlib.Path:
        """Return the absolute path to the sample's freqeuncy map.

        Args:
            sample: The sample to get the frequency map path for.

        Returns:
            The absolute path.
        """

        path = self.path_to(sample)
        # UTAU seems to generate frequency maps with the filename '(sample)_wav.frq'.
        name = path.stem + path.suffix.replace(".", "_") + ".frq"

        return self.dir / name

    def get(self, alias: str) -> Sample | None:
        """Get a sample by its alias.

        Args:
            alias: The sample's alias.

        Returns:
            The sample if found, else None.
        """

        return self.samples.get(alias)

    def __getitem__(self, alias: str) -> Sample:
        return self.samples[alias]

    def __iter__(self) -> Iterator[Sample]:
        return iter(self.samples.values())


def extract_zip(file: str | pathlib.Path | IO[bytes], dir: str | pathlib.Path):
    """Extract a ZIP file which may not be in UTF-8.

    Voicebanks in the form of zipfiles are usually encoded in the OEM locale,
    but since ZIP files only support code page 437 and UTF-8, names end up mojibaked as code page 437.
    Therefore, filenames must be encoded as code page 437 and decoded as the OEM locale to obtain the UTF-8 representation.

    Args:
        file: The ZIP file to extract.
        dir: Where to extract the ZIP file's contents to.

    Raises:
        ValueError: The ZIP encoding could not be detected.
    """

    if isinstance(dir, str):
        dir = pathlib.Path(dir)

    with zipfile.ZipFile(file) as zf:
        # Feed the member filenames as raw bytes to chardet.
        encoding = detect_encoding(n.encode("cp437") for n in zf.namelist())
        if encoding is None:
            raise ValueError("failed to detect zip encoding")

        for zi in zf.infolist():
            # Demojibake the filename.
            name = zi.filename.encode("cp437").decode(encoding)
            path = dir / name

            # Create the parent directory of the file to extract.
            path.parent.mkdir(exist_ok=True)

            # Copy the file to the filesystem with the demojibaked filename.
            with (
                zf.open(zi) as src,
                path.open("wb") as dst,
            ):
                shutil.copyfileobj(src, dst)


def detect_encoding(file: Iterator[bytes]) -> str | None:
    """Determine the encoding of a binary file.

    Args:
        file: The file to detect the encoding of.

    Returns:
        The encoding if detected successfully, otherwise None.
    """

    detector = chardet.UniversalDetector()

    for line in file:
        if not detector.done:
            detector.feed(line)
        else:
            break

    result = detector.close()

    if encoding := result["encoding"]:
        encoding = encoding.lower()

        if encoding == "windows-1252":
            # Shift-JIS may be detected incorrectly as code page 1252 if the oto.ini is too small.
            encoding = "shift_jis"

        return encoding

    return None
