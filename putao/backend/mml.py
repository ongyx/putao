# coding: utf8
"""MMML/M3L (Modern Music Macro Language) parser (with a generous serving of regex).

TODO: Add support for the 'v' (volume) command.
"""

import re
from dataclasses import dataclass
from typing import Any, Generator, cast

from putao import utils


TOKENS = {
    "note": r"([cdefgab][#b]?)(\d+)?",
    "rest": r"[rp](\d+)?",
    "prop": r"([olt])(\d+)",
    "octave_step": r"([<>])",
    "comment": r"# ?(.*)\n",
    "ignore": r"\s",
    "invalid": r".",
}
RE_TOKENS = re.compile(
    "|".join(f"(?P<{name}>{regex})" for name, regex in TOKENS.items())
)


@dataclass
class Token:
    type: str
    value: Any

    def __repr__(self):
        return f"Token(type={self.type}, value={self.value})"


def tokenize(mml: str) -> Generator[Token, None, None]:
    """Turn a string of MML commands into tokens.

    Args:
        mml: The mml commands.

    Raises:
        ValueError, if there was an invalid command.

    Yields:
        A token for each command.
    """

    for match in RE_TOKENS.finditer(mml):
        token_type = cast(str, match.lastgroup)

        # we don't want the full string, just the groups
        raw_value = [v for v in match.groups() if v is not None][1:]

        value: Any

        if token_type == "note":
            try:
                key, length = raw_value
            except ValueError:
                key = raw_value[0]
                length = "0"

            value = (key, int(length))

        elif token_type == "rest":
            if not raw_value:
                value = 0
            else:
                value = int(raw_value[0])

        elif token_type == "prop":
            prop, value = raw_value
            value = (prop, int(value))

        elif token_type == "octave_step":
            step = raw_value[0]
            if step == ">":
                value = 1
            else:
                value = -1

        elif token_type == "comment":
            value = raw_value[0]

        elif token_type == "ignore":
            continue

        elif token_type == "invalid":
            raise ValueError(
                f"invalid token: {match.string[match.start():match.end()]}"
            )

        yield Token(token_type, value)


class Interpreter:
    """Interpret MML commands into putao project songs."""

    def __init__(self, mml: str):

        self.octave = 4
        self.length = utils.NOTE_LENGTH.quarter
        self.bpm = 120

        self.tokens = tokenize(mml)

    def execute(self) -> Generator[dict, None, None]:
        for token in self.tokens:
            if token.type == "note":

                note, length = token.value

                yield {
                    "type": "note",
                    # In mml, we use a 'global' octave so we have to calculate the semitone here.
                    "pitch": utils.semitone(f"{note}{self.octave}"),
                    "duration": utils.duration(length or self.length, self.bpm),
                }

            elif token.type == "rest":

                length = token.value

                yield {
                    "type": "rest",
                    "duration": utils.duration(length or self.length, self.bpm),
                }

            elif token.type == "prop":

                prop, value = token.value
                if prop == "o":
                    self.octave = value
                elif prop == "l":
                    self.length = value
                elif prop == "t":
                    self.bpm = value

            elif token.type == "octave_step":

                self.octave += token.value


def loads(data):
    itpr = Interpreter(data.decode("utf8"))
    for note in itpr.execute():
        yield note
