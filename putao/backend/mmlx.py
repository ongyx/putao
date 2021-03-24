# coding: utf8
"""mmlx (Music Macro Language eXtended) parser and interpreter.

TODO
- add support for ADSR envelopes through 'v' command.

(Anything enclosed in '[]' is optional.)

Core syntax:

    lengths below may be one of '1', '2', '4', '8', '16', '32', '64'
    (1 -> whole note, 2 -> half note, 4 -> quarter note, 8 -> eighth note, etc.)

    (key)[accidental][length]
        Play a note.

        key must be one of the letters 'abcdefg',
        and accidental may be '+', '#' (sharp) or '-' (flat).
        i.e 'c2'

    p[length] / r[length]
        Pause/rest playing notes.

    o(octave)
        Change the octave of the notes.

        octave must be a integer.

    > / <
        Shift octave up or down, respectively.

    l(length)
        Change the length of the notes.

    t(tempo)
        Change the tempo of the notes.

        tempo must be an integer, in beats per minute.

Extended syntax:

    #[comment]
        A comment.
        Comments can appear anywhere in a line (i.e after commands).
        All text between the '#' until the next newline is ignored.

    @(trackname)
        Add any notes after this to trackname.
        Any notes without a specified track are implictly added to the 'global' track.

    |(lyrics)
        Add lyrics to the current track, split by whitespace.
        Each split is a phoneme.
"""

import collections
from dataclasses import dataclass
from typing import Any, Dict, List

import pyparsing as pp

from putao import utils

pp_u = pp.pyparsing_unicode


PROPMAP = {"o": "octave", "l": "length", "t": "tempo"}


@dataclass
class Token:
    name: str
    value: Any
    loc: int


def _note(loc, tk):
    try:
        key, length = tk[0]
        length = int(length)
    except ValueError:
        key = tk[0][0]
        length = 0

    # the none is a placeholder for a phoneme.
    return Token("note", (key, length), loc)


def _rest(loc, tk):
    return Token("rest", tk[0], loc)


def _prop(loc, tk):
    try:
        prop, value = tk[0]
        value = int(value)
        shift = False

    except ValueError:
        prop = "o"
        value = tk[0]

        if value == "<":
            value = -1
        elif value == ">":
            value = 1

        shift = True

    return Token("prop", (prop, value, shift), loc)


def _oct_shift(loc, tk):
    return Token("oct_shift", 1 if tk[0] == ">" else -1, loc)


def _track(loc, tk):
    return Token("track", tk[0], loc)


def _lyrics(loc, tk):
    return Token("lyrics", tk[0].split(), loc)


# core MML syntax
def _mml_syntax():
    key = pp.Combine(pp.Char("cdefgab") + pp.Optional(pp.Char("+-#")))
    key.setParseAction(lambda tk: tk[0].replace("+", "#").replace("-", "b"))

    length = pp.Optional(pp.Word(pp.nums))

    note = pp.Group(key + length)
    note.setParseAction(_note)

    rest = pp.Combine((pp.Suppress("r") | pp.Suppress("p")) + length)
    rest.setParseAction(_rest)

    prop_num = pp.Word(pp.nums)

    prop = pp.Group(pp.Char("olt") + prop_num)
    prop.setParseAction(_prop)

    oct_shift = pp.Char("<>")
    oct_shift.setParseAction(_oct_shift)

    mml = (note | rest | prop | oct_shift)[1, ...]

    # eXtended syntax
    comment = pp.Literal("#") + pp.restOfLine

    track = pp.Suppress("@") + pp.Word(pp.alphanums)

    lyrics = pp.Suppress("|") + pp.Word(pp.alphanums + pp_u.Japanese.printables)

    mmlx = mml | comment | track | lyrics
    mmlx.ignore(comment)

    return mmlx


Parser = _mml_syntax()


class Interpreter:
    def __init__(self, mml: str):
        self._tokens = Parser.parseString(mml)
        # per-track variables
        self._props = {
            "global": {
                "octave": 4,
                "length": utils.NOTE_LENGTH.quarter,
                "tempo": 120,
                "lyrics": [],
            }
        }

        self.tracks: Dict[str, List[dict]] = collections.defaultdict(list)
        self.current_track = "global"

    def _prop(self) -> dict:
        return self._props.setdefault(self.current_track, self._props["global"])

    def note(self, token, track):
        key, length = token.value

        note = {
            "type": "note",
            # In mml, we use a 'global' octave so we have to calculate the semitone here.
            "pitch": utils.Pitch(note=f"{key}{track['octave']}").semitone,
            "duration": utils.duration(length or track["length"], track["tempo"]),
        }

        if track["lyrics"]:
            note["phoneme"] = next(track["lyrics"])

        self.tracks[self.current_track].append(note)

    def rest(self, token, track):
        length = token.value

        self.tracks[self.current_track].append(
            {
                "type": "rest",
                "duration": utils.duration(length or track["length"], track["tempo"]),
            }
        )

    def prop(self, token, track):
        prop, value, shift = token.value
        if shift:
            track[PROPMAP[prop]] += value
        track[PROPMAP[prop]] = int(value)

    def oct_shift(self, token, track):
        track["octave"] += token.value

    def track(self, token, track):
        self.current_track = token.value

    def lyrics(self, token, track):
        track["lyrics"] = iter(token.value)

    def execute(self):
        for token in self._tokens:
            getattr(self, token.name)(token, self._prop())

        return {"tracks": dict(self.tracks)}


def loads(data):
    itpr = Interpreter(data.decode("utf8"))
    return itpr.execute()
