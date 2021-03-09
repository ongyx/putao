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

'##(lyrics)':

    Map each syllable in lyrics (split by spaces) to the corrosponding note on the next line.

##o shi e te o shi e te o so no shi ku mi wo
a b2 a2 a-2 f+ r b2 a2 a-2 f+ r f+ e2 r d2 d2 c

TODO:
    Add support for the 'v' (volume) command.
"""

import collections
import copy
import re
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, cast

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
PROPS = {"o": "octave", "l": "length", "t": "bpm"}
GLOBAL_PROPS = {
    "global": {
        "octave": OCTAVE,
        "length": utils.NOTE_LENGTH.quarter,
        "bpm": BPM,
        "lyrics": [],
        "lyrics_counter": 0,
    }
}


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
        value = [v for v in match.groups() if v is not None][1:]

        if token_type == "invalid":
            raise ValueError(
                f"invalid token: {match.string[match.start():match.end()]}"
            )

        yield Token(token_type, value)


class Interpreter:
    """Interpret MML commands into putao project songs."""

    def __init__(self, mml: str):
        self.tokens = tokenize(mml)

        # stores per-track properties
        self.props = copy.deepcopy(GLOBAL_PROPS)

        self.tracks: Dict[str, List[dict]] = collections.defaultdict(list)
        self.current_track = "global"

    def _prop(self) -> dict:
        return self.props.setdefault(self.current_track, self.props["global"])

    def note(self, token, track):
        try:
            key, length = token.value
        except ValueError:
            key = token.value[0]
            length = "0"

        length = int(length)

        key = key.replace("+", "#").replace("-", "b")

        note = {
            "type": "note",
            # In mml, we use a 'global' octave so we have to calculate the semitone here.
            "pitch": utils.semitone(f"{key}{track['octave']}"),
            "duration": utils.duration(length or track["length"], track["bpm"]),
        }

        if track["lyrics"]:
            counter = track["lyrics_counter"]

            try:
                syllable = track["lyrics"][counter]
            except IndexError:
                syllable = track["lyrics"][-1]

            note["syllable"] = syllable
            track["lyrics_counter"] += 1

        self.tracks[self.current_track].append(note)

    def rest(self, token, track):
        if not token.value:
            length = track["length"]
        else:
            length = int(token.value[0])

        self.tracks[self.current_track].append(
            {"type": "rest", "duration": utils.duration(length, track["bpm"])}
        )

    def prop(self, token, track):
        prop, value = token.value
        propname = PROPS[prop]
        track[propname] = int(value)

    def octave_step(self, token, track):
        step = token.value[0]
        if step == ">":
            octave = 1
        else:
            octave = -1

        track["octave"] += octave

    def comment(self, token, track):
        comment = token.value[0]
        if comment.startswith("#"):
            track["lyrics"] = comment[1:].split()

    def track(self, token, track):
        self.current_track = token.value[0]

    def ignore(self, token, track):
        pass

    def execute(self) -> dict:
        self.tracks.clear()

        for token in self.tokens:

            t_prop = self._prop()
            getattr(self, token.type)(token, t_prop)

        return dict(self.tracks)


def loads(data):
    itpr = Interpreter(data.decode("utf8"))
    return itpr.execute()
