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


@dataclasses.dataclass
class Section:
    """An INI section, i.e. [name]."""

    name: str


@dataclasses.dataclass
class Property:
    """An INI property, i.e. key=value."""

    key: str
    value: str


def parse(line: str) -> Section | Property | None:
    """Parse a line of ini-like config.

    Args:
        line: The line to parse.

    Returns:
        A section, property, or None if the line failed to parse.
    """

    if m := REGEX.match(line):
        if section := m["section"]:
            return Section(section)
        else:
            # The group dictionary must contain key and value.
            return Property(key=m["key"], value=m["value"])

    return None
