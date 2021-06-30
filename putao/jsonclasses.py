# coding: utf8
"""Wraps the json module to allow (de)serializing dataclasses.
(As long as your dataclass uses only the basic JSON types, no nested classes.)

To use, just replace any `dataclasses` import with `jsonclasses`.
jsonclasses automatically monkeypatches the json module so that it can dump any dataclasses created using the `@jsonclasses.dataclass` decorator.

NOTE: Any dataclass fields that start with `_` (i.e `_data`) **will** be treated as private and will not be serialised.
"""

import functools
import json
from dataclasses import (
    dataclass as _dataclass,
    field,
    Field,
    FrozenInstanceError,
    InitVar,
    MISSING,
    fields,
    asdict,
    astuple,
    make_dataclass,
    replace,
    is_dataclass,
)
from typing import Any, Dict

__all__ = [
    "dataclass",
    "field",
    "Field",
    "FrozenInstanceError",
    "InitVar",
    "MISSING",
    "fields",
    "asdict",
    "astuple",
    "make_dataclass",
    "replace",
    "is_dataclass",
]


_DATACLASSES: Dict[str, Any] = {}


def dataclass(cls=None, **kwargs):
    def wrap(cls):
        _DATACLASSES[cls.__name__] = cls
        return _dataclass(cls, **kwargs)

    if cls is None:
        return wrap

    return wrap(cls)


def _encode(o):
    if is_dataclass(o):
        new_o = {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
        new_o["__dataclass__"] = o.__class__.__name__
        return new_o

    return json.JSONEncoder().default(o)


def _decode(o):
    if "__dataclass__" in o:
        cls = _DATACLASSES[o.pop("__dataclass__")]
        return cls(**o)
    return o


# monkey-patch load(s) and dump(s)
json.loads = functools.partial(json.loads, object_hook=_decode)
json.load = functools.partial(json.load, object_hook=_decode)
json.dumps = functools.partial(json.dumps, default=_encode)
json.dump = functools.partial(json.dump, default=_encode)
