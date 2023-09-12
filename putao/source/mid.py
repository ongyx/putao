# coding: utf8

import io

import mido

from . import source


class Source(source.Source):
    """MIDI source.

    If the midi track to import into the project has chords, each note of the chord is seperated into it's own track.

    Options:
        midi.track: Which track to use as the lead. If track < 0, all tracks are merged.
            Defaults to -1.
    """

    def loads(self, data, project):
        mid = mido.MidiFile(file=io.BytesIO(data))

        track_n = project.config.options.setdefault("midi.track", -1)
        if track_n < 0:
            track = mido.merge_tracks(mid.tracks)
        else:
            track = mid.tracks[track_n]

        clock = 0
        clock_prev = 0
        track_index = 0

        note = None

        for msg in track:
            clock += msg.time

            if not self.is_start(msg):
                continue

            if clock != clock_prev:
                track_index = 0

    def is_start(self, note):
        try:
            return note.type == "note_on" and note.velocity != 0
        except AttributeError:
            return False
