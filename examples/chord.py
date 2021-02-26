# coding: utf8

import json

import putao


proj = putao.Project()
track = proj.new_track()
track.note("sine", 60, 5.0)
track.note("sine", 67, 5.0, 2.5)
proj.render("test.wav")

with open("test.json", "w") as f:
    json.dump(proj.dump_dict(), f, indent=4)
