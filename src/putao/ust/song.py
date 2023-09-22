import io
import pathlib
import re
from typing import Iterator, Self, TextIO

from .. import ini

NOTE_LIMIT = 10000

RE_VERSION = re.compile(r"^UST Version(.+?)$", flags=re.IGNORECASE)
RE_NOTE = re.compile(r"#\d{4}")


# Custom parser for UST files.
def _parse(line: str) -> ini.Section | ini.Property | None:
    if config := ini.parse(line):
        if isinstance(config, ini.Property):
            # Casing for UST properties are inconsistent.
            config.key = config.key.lower()

        return config

    # Replace version declaration with a valid INI property.
    if match := RE_VERSION.match(line):
        return ini.Property("version", match.group(1))

    return None


class Song:
    """An arrangement of notes.

    UTAU Sequence Texts are ini-like files with several sections:
    * `#VERSION`: UST version in the format `UST Version(version)`.
    * `#SETTING`: Settings for the UST name and track rendering.
    * `#0000` to `#9999`: The track notes.
    * `#TRACKEND`: End of track marker.

    Attributes:
        version: The UST version.
        settings: Rendering configuration for the UST.
        notes: The UST notes.

    Args:
        file: The UST file to parse into a song.

    Raises:
        ValueError: Parsing the UST file failed.
    """

    version: str
    settings: dict[str, str]
    notes: list[dict[str, str]]

    def __init__(self, file: Iterator[str]):
        config = ini.load(file, parse_func=_parse)

        self.version = config["#VERSION"]["version"]

        self.settings = dict(config["#SETTING"])

        # Assuming notes are in contiguous order.
        self.notes = [p for s, p in config.items() if RE_NOTE.match(s)]

    def save(self, file: TextIO):
        """Save the song in UST format.

        Args:
            file: The file to save to.
        """

        if len(self.notes) > NOTE_LIMIT:
            raise ValueError(f"too many notes: the limit is {NOTE_LIMIT}")

        # Manually serialize UST version.
        ini.dump({"#VERSION": {}}, file)
        print(f"UST Version{self.version}", file=file)

        config = (
            # UST settings.
            {"#SETTING": self.settings}
            # UST notes (#0000 to #9999 max)
            | {f"#{i:0>4}": note for i, note in enumerate(self.notes)}
            # Track end marker.
            | {"#TRACKEND": {}}
        )

        ini.dump(config, file)

    @classmethod
    def from_str(cls, text: str) -> Self:
        """Parse a UST text into a song.

        Args:
            text: The UST text to parse.

        Returns:
            The parsed song.
        """

        with io.StringIO(text) as buf:
            return cls(buf)
