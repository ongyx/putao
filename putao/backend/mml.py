# coding: utf8
"""MMML/M3L (Modern Music Macro Language) parser (with a generous serving of regex).
See https://en.wikipedia.org/wiki/Music_Macro_Language for syntax.
All commands except "v" are currently supported.

This parser also defines putao-specific extensions:

'@(track_name)':

    Any commands after this will apply only to track_name.
    All tracks start at the same time, t=0.
    This can be used for sub-voices:

o5 t240  # 'global' settings, applies to all tracks

@lead  # must be on it's own line!
c4

@sub
>c4

'#[L](lyrics)':

    Map each syllable in lyrics (split by spaces) to the corrosponding note on the next line.

#[L]o shi e te o shi e te o so no shi ku mi wo
a b2 a2 a-2 f+ r b2 a2 a-2 f+ r f+ e2 r d2 d2 c

TODO:
    Add support for the 'v' (volume) command.
    Multiple tracks (using @ notation).
"""

import re
from dataclasses import dataclass
from typing import Any, Generator, List, cast

from putao import utils


OCTAVE = 4
BPM = 120
TOKENS = {
    "note": r"([cdefgab][#\+\-]?)(\d+)?",
    "rest": r"[rp](\d+)?",
    "prop": r"([olt])(\d+)",
    "octave_step": r"([<>])",
    "comment": r"# ?(.*)\n",
    "track": r"@(.*)\n",
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


def _parse(token_type, raw_value):
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

    elif token_type in ("comment", "track"):
        value = raw_value[0]

    elif token_type == "ignore":
        return

    elif token_type == "invalid":
        raise ValueError

    return value


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

        try:
            value: Any = _parse(token_type, raw_value)
        except ValueError:
            raise ValueError(
                f"invalid token: {match.string[match.start():match.end()]}"
            )

        if value is None:
            continue

        yield Token(token_type, value)


class Interpreter:
    """Interpret MML commands into putao project songs."""

    def __init__(self, mml: str):

        self.octave = OCTAVE
        self.length = utils.NOTE_LENGTH.quarter
        self.bpm = BPM

        self.tokens = tokenize(mml)

    def execute(self) -> Generator[dict, None, None]:

        lyrics: List[str] = []
        lyrics_counter = 0

        for token in self.tokens:

            if token.type == "note":
                note, length = token.value
                note = note.replace("+", "#").replace("-", "b")

                note = {
                    "type": "note",
                    # In mml, we use a 'global' octave so we have to calculate the semitone here.
                    "pitch": utils.semitone(f"{note}{self.octave}"),
                    "duration": utils.duration(length or self.length, self.bpm),
                }

                if lyrics:
                    note["syllable"] = lyrics[lyrics_counter]
                    lyrics_counter += 1

                yield note

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

            elif token.type == "comment":
                if token.value.startswith("[L]"):
                    # it is a lyric comment
                    lyrics = token.value[3:].split()


def loads(data):
    itpr = Interpreter(data.decode("utf8"))
    # only one track for now
    return {"0": [note for note in itpr.execute()]}
