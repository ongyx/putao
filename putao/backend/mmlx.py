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

    @(extension) [args] {...}
        General syntax for an extension.
        Extensions can modify/apply changes to the notes within its scope (the '{...}').

    @track (trackname) {...}
        Add scoped notes to trackname.
        Any notes outside of a @track scope are implictly added to the 'global' track.

    @loop (times) {...}
        Repeat scoped notes by number of times.
        times must be an integer.

    @lyrics (syllables) {...}
        Add lyrics (split by spaces) to the scoped notes.
        If there are not enough syllables, the last one will be repeated for the rest of the notes.
"""

import collections
from dataclasses import dataclass
from typing import Any, Dict, List

import pyparsing as pp

from putao import utils


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

    # the none is a placeholder for a syllable.
    return Token("note", (key, length, None), loc)


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


def _scope_header(loc, tk):
    return Token("scope", list(tk[0]), loc)


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

    scope = pp.Forward()
    scope_header = pp.Group(
        pp.Combine(pp.Suppress("@") + pp.Word(pp.alphas)) + pp.Word(pp.alphanums)[...]
    )
    scope_header.setParseAction(_scope_header)

    inner_scope = pp.Group(pp.Suppress("{") + scope + pp.Suppress("}"))

    scope << ((scope_header + inner_scope) | scope_header | mml)[1, ...]

    mmlx = (mml | comment | scope)[1, ...]
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
            }
        }

        self.tracks: Dict[str, List[dict]] = collections.defaultdict(list)
        self.current_track = "global"

    def _prop(self) -> dict:
        return self._props.setdefault(self.current_track, self._props["global"])

    def note(self, token, track):
        key, length, syllable = token.value

        note = {
            "type": "note",
            # In mml, we use a 'global' octave so we have to calculate the semitone here.
            "pitch": utils.semitone(f"{key}{track['octave']}"),
            "duration": utils.duration(length or track["length"], track["tempo"]),
        }

        if syllable is not None:
            note["syllable"] = syllable

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

    def scope_track(self, args, tokens, track):
        self.current_track = args[0]

    def scope_loop(self, args, tokens, track):
        times = int(args[0]) - 1
        for _ in range(times):
            tokens.extend(tokens)

    def scope_lyrics(self, args, tokens, track):
        lyrics = iter(args)
        last_syllable = args[-1]

        for token in tokens:
            if token.name == "scope":
                raise RuntimeError("scopes are not allowed within lyrics")

            if token.name == "note":
                key, length, _ = token.value
                token.value = (key, length, next(lyrics, last_syllable))

    def _execute(self, tokens):
        counter = 0
        limit = len(tokens)

        while counter < limit:
            token = tokens[counter]
            track = self._prop()

            if token.name != "scope":
                getattr(self, token.name)(token, track)

            else:
                # the next token is actually a list of tokens under this scope
                # so take the next one
                try:
                    scope_tokens = tokens[counter + 1]
                except IndexError:
                    scope_tokens = []
                name, *args = token.value

                try:
                    getattr(self, f"scope_{name}")(args, scope_tokens, track)
                except AttributeError:
                    raise RuntimeError(f"{name}: no such extension exists")

                self._execute(scope_tokens)

                # skip the scoped tokens
                counter += 1

            counter += 1

    def execute(self):
        self.tracks.clear()
        self._execute(self._tokens)
        return dict(self.tracks)


def loads(data):
    itpr = Interpreter(data.decode("utf8"))
    return itpr.execute()
