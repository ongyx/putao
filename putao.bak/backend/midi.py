# coding: utf8

import io
from dataclasses import dataclass
from typing import List

import mido


@dataclass
class Note:
    # absolute start/end
    start: int
    end: int
    pitch: int
    tpb: int
    tempo: int

    def dump(self):
        return {
            "type": "note",
            "pitch": self.pitch,
            "duration": mido.tick2second(self.end - self.start, self.tpb, self.tempo),
        }


def _collides(note1: Note, note2: Note) -> bool:
    return (note2.start <= note1.start < note2.end) or (
        note2.start < note1.end <= note2.end
    )


def _tempo(meta):
    clock = 0
    changes = []
    for msg in meta:
        clock += msg.time
        if msg.type == "set_tempo":
            changes.append((clock, msg.tempo))

    return changes


class Song:
    def __init__(self, data: bytes):
        buf = io.BytesIO(data)
        mid = mido.MidiFile(file=buf)

        self.notes: List[Note] = []

        meta = mid.tracks[0]
        if any(msg.type == "note_on" for msg in meta):
            # lead is also meta
            lead = meta
        else:
            lead = mid.tracks[5]

        tempos = _tempo(meta)

        clock = 0
        next_clock = 0
        current_tempo = tempos[0][1]
        tempo_counter = 0

        for count, msg in enumerate(lead):
            clock += msg.time

            if msg.type != "note_on":
                continue

            next_clock = clock
            for next_count, next_msg in enumerate(lead[count + 1 :]):
                next_clock += next_msg.time
                if next_msg.type == "note_off" and next_msg.note == msg.note:
                    break

            # apply change in tempo (if any)
            if not (tempo_counter >= len(tempos)):
                tempo_clock, tempo = tempos[tempo_counter]
                if clock <= tempo_clock <= next_clock:
                    current_tempo = tempo
                    tempo_counter += 1

            self.notes.append(
                Note(clock, next_clock, msg.note, mid.ticks_per_beat, current_tempo)
            )

    def dump(self) -> List[dict]:
        track: List[dict] = []

        for count, note in enumerate(self.notes):
            prev_note = self.notes[count - 1]
            note_dump = note.dump()

            if note.start > 0:

                # there is a rest between this note and the previous one
                if count >= 1:
                    interval = note.start - prev_note.end
                else:
                    # first note, but there is a pause at the start
                    interval = note.start

                rest = mido.tick2second(interval, note.tpb, note.tempo)

                if rest < 0:
                    # overlapping notes
                    note_dump["overlap"] = abs(rest)

                else:
                    track.append(
                        {
                            "type": "rest",
                            "rest": rest,
                        }
                    )

            track.append(note_dump)

        return track


def loads(data: bytes):
    return Song(data).dump()
