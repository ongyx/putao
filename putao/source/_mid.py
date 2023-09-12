# coding: utf8
"""MIDI backend parser.
NOTE: If a note overlaps with the next, it will be truncated to the start of the next note!
"""


import io
from dataclasses import dataclass
from typing import List

import mido


@dataclass
class Event:
    # start and end is absolute (midi ticks)
    start: int
    end: int
    pitch: int
    tpb: int
    tempo: int

    def dump(self):
        return {
            "type": "note",
            "pitch": self.pitch,
            "duration": int(
                mido.tick2second(self.end - self.start, self.tpb, self.tempo) * 1000
            ),
        }

    def __eq__(self, event):
        if isinstance(event, Event):
            return self.pitch == event.pitch
        else:
            return NotImplemented


class Song:
    def __init__(self, data: bytes):
        self.buf = io.BytesIO(data)
        self.mid = mido.MidiFile(file=self.buf)
        self.events: List[Event] = []

        self.parse()

    def parse(self):

        clock = 0
        next_clock = 0

        meta = self.mid.tracks[0]
        meta_clock = 0

        if any(msg.type == "note_on" for msg in meta):
            # lead is also meta
            lead = meta
        else:
            lead = self.mid.tracks[1]

        tempo = []
        tempo_counter = 0
        for msg in meta:
            meta_clock += msg.time

            if msg.type == "set_tempo":
                tempo.append((msg.tempo, meta_clock))

        for count, msg in enumerate(lead):
            clock += msg.time

            current_tempo = tempo[tempo_counter]

            try:
                next_tempo = tempo[tempo_counter + 1]

            except IndexError:
                pass

            else:
                if next_tempo[1] <= clock:
                    # tempo change
                    current_tempo = next_tempo
                    tempo_counter += 1

            if msg.type == "note_on":
                next_clock = clock

                for next_count, next_msg in enumerate(lead[count + 1 :]):
                    next_clock += next_msg.time

                    if next_msg.type == "note_off" and next_msg.note == msg.note:
                        break

                self.events.append(
                    Event(
                        clock,
                        next_clock,
                        msg.note,
                        self.mid.ticks_per_beat,
                        current_tempo[0],
                    )
                )

    def dump(self):
        notes = []

        for count, event in enumerate(self.events):
            try:
                next_event = self.events[count + 1]
            except IndexError:
                next_event = None

            if next_event is not None:
                rest = next_event.start - event.end

                if rest == 0:
                    # dump note verbatim.
                    notes.append(event.dump())

                elif rest > 0:
                    notes.append(event.dump())

                    # add a rest
                    notes.append(
                        {
                            "type": "rest",
                            "duration": int(
                                mido.tick2second(rest, event.tpb, event.tempo) * 1000
                            ),
                        }
                    )

                elif rest < 0:
                    # overlapping notes, truncate previous one
                    event.end = next_event.start

                    notes.append(event.dump())

            notes.append(event.dump())

        return {"lead": notes}


def loads(data):
    return Song(data).dump()
