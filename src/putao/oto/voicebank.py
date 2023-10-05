import functools
import io
import pathlib
import shutil
import zipfile
from collections import UserDict
from collections.abc import Iterator
from typing import IO

import chardet
from rich.progress import Progress

from .. import audio

from .frq import Frq
from .sample import Sample

CONFIG_FILE = "oto.ini"


class Voicebank(UserDict[str, Sample]):
    """A collection of voice samples.

    A typical UTAU voicebank contains an `oto.ini` configuration file,
    any number of waveform voice samples (`.wav`), and frequenecy maps (`.frq`) for those samples.

    Attributes:
        dir: The directory where the samples reside.
            An oto.ini file must be present inside the directory.
        config: The path to the oto.ini file.
        encoding: The file encoding of the oto.ini.
            If None, encoding detection is attempted.

    Args:
        check: Whether or not to perform a sanity check on the voicebank.
            Defaults to True.

    Raises:
        ValueError: The encoding could not be detected or the sanity check failed.
    """

    dir: pathlib.Path
    config: pathlib.Path
    encoding: str

    def __init__(
        self, dir: str | pathlib.Path, encoding: str | None = None, check: bool = True
    ):
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
            samples = (Sample.parse(line) for line in f)

            super().__init__({s.alias: s for s in samples})

        if check:
            for sample in self:
                if not self.path_to(sample).exists():
                    raise ValueError(
                        f"sample in oto.ini not found: '{sample.file}' aliased by '{sample.alias}'"
                    )

    def path_to(self, sample: Sample) -> pathlib.Path:
        """Return the absolute path to the sample's audio file.

        Args:
            sample: The sample to get the audio file path for.

        Returns:
            The absolute path.
        """

        return self.dir / sample.file

    @functools.cache
    def load(self, sample: Sample) -> audio.Segment:
        """Load a sample as an audio segment.

        Args:
            sample: The sample to load the audio segment for.

        Returns:
            The audio segment.
        """

        return audio.Segment.from_file(self.path_to(sample))

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

    @functools.cache
    def load_frq(self, sample: Sample) -> Frq:
        """Load a sample's frequency map.

        Args:
            sample: The sample to load the frequency map for.

        Returns:
            The frequency map.
        """

        with self.path_to_frq(sample).open("rb") as f:
            return Frq.load(f)

    def __iter__(self) -> Iterator[Sample]:
        return iter(self.data.values())


def extract_zip(
    file: str | pathlib.Path | IO[bytes],
    dir: str | pathlib.Path,
    *,
    progress: Progress | None = None,
):
    """Extract a ZIP file which may not be in UTF-8.

    Voicebanks in the form of zipfiles are usually encoded in the OEM locale,
    but since ZIP files only support code page 437 and UTF-8, names end up mojibaked as code page 437.
    Therefore, filenames must be encoded as code page 437 and decoded as the OEM locale to obtain the UTF-8 representation.

    Args:
        file: The ZIP file to extract.
        dir: Where to extract the ZIP file's contents to.
        progress: If not None, extraction progress is reported.

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

        # Wrap infolist to track progress.
        zil = zf.infolist()
        if progress is not None:
            zil = progress.track(zil, description=f"Extracting {file}")

        for zi in zil:
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
