# coding: utf8

from dataclasses import dataclass
from typing import Any

import pyparsing as pp


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

    return Token("note", (key, length), loc)


def _rest(loc, tk):
    return Token("rest", tk[0], loc)


def _prop(loc, tk):
    prop, value = tk[0]
    if value == "<":
        value = -1
    elif value == ">":
        value = 1
    else:
        value = int(value)

    return Token("prop", (prop, value), loc)


# core MML syntax
key = pp.Combine(pp.Char("cdefgab") + pp.Optional(pp.Char("+-#")))
key.setParseAction(lambda tk: tk[0].replace("+", "#").replace("-", "b"))

length = pp.Optional(pp.Word(pp.nums))

note = pp.Group(key + length)
note.setParseAction(_note)

rest = pp.Combine((pp.Suppress("r") | pp.Suppress("p")) + length)

prop_num = pp.Word(pp.nums)

prop = pp.Group(pp.Char("olt") + prop_num) | pp.Char("<>")
prop.setParseAction(_prop)

mml = (note | rest | prop)[1, ...]

# eXtended syntax
comment = pp.Literal("#") + pp.restOfLine

left_brace = pp.Suppress("{")
right_brace = pp.Suppress("}")
scope = pp.Forward()
scope << (
    pp.Group(
        pp.Combine(pp.Suppress("@") + pp.Word(pp.alphas)) + pp.Word(pp.alphanums)[...]
    )
    + pp.Group(left_brace + scope + right_brace)
    | mml
)

mmlx = (mml | comment | scope)[1, ...]
mmlx.ignore(comment)


if __name__ == "__main__":
    sample = """
    # lol
    c2defgab
    @track lol lol {
        @loop 1 {
            cdefgab
        }
    }
    """
    for t in mmlx.parseString(sample):
        print(t)
