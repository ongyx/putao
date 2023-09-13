import dataclasses
import enum
import re
from collections.abc import Iterator
from typing import Literal, Self, TextIO

REGEX = re.compile(
    r"""
    # Anchor to the start of the line.
    ^

    # Match a section...
    (?:\[(?P<section>.+?)\])
    # or a property (Whitespace around the equals sign is ignored).
    | (?:(?P<key>.+?) (?:\s*) = (?:\s*) (?P<value>.*?))

    # Anchor to the end of the line.
    $
    """,
    flags=re.VERBOSE,
)


class ParseError(ValueError):
    """Exception raised when parsing an ini-like config fails.

    Attributes:
        line: The line which failed to parse.
        line_number: The line number.
    """

    line: str
    line_number: int

    def __init__(self, *args, line: str = "", line_number: int = 0):
        super().__init__(*args)

        self.line = line
        self.line_number = line_number


@dataclasses.dataclass
class Section:
    """An INI section, i.e. [name]."""

    name: str


@dataclasses.dataclass
class Property:
    """An INI property, i.e. key=value."""

    key: str
    value: str


Config = Section | Property


def parse(line: str) -> Config:
    """Parse an ini-like line of text into configuration.

    Args:
        line: The line to parse.

    Returns:
        The parsed config.

    Raises:
        ParseError: The line failed to parse.
    """

    if m := REGEX.match(line):
        if section := m["section"]:
            return Section(section)
        else:
            # The group dictionary must contain key and value.
            return Property(key=m["key"], value=m["value"])

    raise ParseError("invalid ini config", line=line)


def parse_file(file: TextIO) -> Iterator[Config]:
    """Parse an ini-like file.

    Args:
        file: The ini-like file.

    Yields:
        The config for each line in the file.

    Raises:
        ParseError: Parsing any of the lines failed.
    """

    for line_number, line in enumerate(file):
        try:
            yield parse(line)
        except ParseError as e:
            # Add more context to the parse error.
            e.line_number = line_number
            raise e
