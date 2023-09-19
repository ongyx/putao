import dataclasses
import enum
import io
import re
from collections.abc import Iterator, Callable
from typing import Literal, Self, TextIO

Config = dict[str, dict[str, str]]

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


@dataclasses.dataclass(slots=True)
class Section:
    """An INI section, i.e. [name]."""

    name: str


@dataclasses.dataclass(slots=True)
class Property:
    """An INI property, i.e. key=value."""

    key: str
    value: str


def parse(line: str) -> Section | Property | None:
    """Parse an INI line.

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


def load(
    file: Iterator[str],
    default_section: str = "DEFAULT",
    parse_func: Callable[[str], Section | Property | None] = parse,
) -> Config:
    """Parse an INI file.

    Args:
        file: The file to parse.
        lowercase: Whether or not to lowercase property keys.
        default_section: The section to put properties in if no sections are specified.
            Defaults to "DEFAULT".
        parse_func: A function that returns a section, property, or None per line in the file.
            This function can be overriden to implement custom functionality.
            Defaults to parse.

    Returns:
        A dictionary of sections mapped to their properties.

    Raises:
        ValueError: parse_func returned None for any line in the file.
    """

    config: Config = {}
    section = default_section

    for n, line in enumerate(file):
        # Skip blank lines.
        if not line.strip():
            continue

        if cfg := parse_func(line):
            if isinstance(cfg, Section):
                section = cfg.name
            else:
                config.setdefault(section, {})[cfg.key] = cfg.value

        else:
            raise ValueError(f"invalid INI on line {n}: '{line}'")

    return config


def loads(text: str, **kwargs) -> Config:
    """Parse an INI text.

    Args:
        text: The text to parse.
        **kwargs: Passed to load().

    Returns:
        See load().

    Raises:
        See load().
    """

    # Since we're parsing with regular expressions,
    # keeping newlines shouldn't make a difference but leave them anyway.
    return load(iter(text.splitlines(keepends=True)))


def dump(config: Config, file: TextIO):
    """Serialize a dictionary as INI to a file.

    Args:
        config: The dictionary of sections mapped to properties.
        file: The file to serialize to.
    """

    for section, properties in config.items():
        print(f"[{section}]", file=file)

        for key, value in properties.items():
            print(f"{key}={value}", file=file)


def dumps(config: Config) -> str:
    """Serialize a dictionary as INI to a string.

    Args:
        config: The dictionary of sections mapped to properties.

    Returns:
        The INI as a string.
    """

    with io.StringIO() as buf:
        dump(config, buf)
        return buf.getvalue()
