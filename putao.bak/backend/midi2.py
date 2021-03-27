# coding: utf8

from dataclasses import dataclass
from typing import Literal

import mido


@dataclass
class Event:
    type: Literal["note", "rest", "set_tempo"]
    # start and end is absolute (midi ticks)
    start: int
    end: int
    pitch: int
    tpb: int
    tempo: int

    def dump(self):
        return {
            "type": self.type,
            "pitch": self.pitch,
            "duration": mido.tick2second(self.end - self.start, self.tpb, self.tempo),
        }

    def __eq__(self, event):
        if isinstance(event, Event):
            return self.pitch == event.pitch
        else:
            return NotImplemented
