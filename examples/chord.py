# coding: utf8

import json

import putao


proj = putao.Project()
track = proj.new_track("lead")
track.note("sine", 60, 10.0)
track.note("sine", 67, 10.0, putao.OVERLAP_START)
track.note("sine", 72, 10.0, putao.OVERLAP_START)
proj.render("test.wav")

with open("test.json", "w") as f:
    json.dump(proj.dump_dict(), f, indent=4)
