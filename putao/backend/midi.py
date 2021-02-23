# coding: utf8

import io

import mido


def loads(data):
    buf = io.BytesIO(data)
    mid = mido.MidiFile(file=buf)

    lead = mid.tracks[1]

    clock = 0.0
    for count, msg in enumerate(lead):
        if msg.type != "note_on":
            continue

        # rests are the msg's time.
        yield {"type": "rest", "duration": msg.time}

        duration = None
        clock += msg.time

        for next_msg in lead[count + 1 :]:
            next_clock = clock

            if not (next_msg.type == "note_off" and next_msg.note == msg.note):
                continue

            next_clock += next_msg.time
            duration = next_clock - clock
            break

        yield {"type": "note", "pitch": msg.note, "duration": duration}
