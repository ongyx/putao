# coding: utf8

from putao import core, backend, utils

vb_path = "./voicebank"

vb_pitch = utils.Pitch(
    note=input("what is the pitch of this voicebank? (i.e C4, D#5, etc.) > ")
).semitone

proj = core.Project(vb_path, vb_pitch)

file = input("path to the mml file you want to render > ")

with open(f"{file}.mml", "rb") as f:
    proj_data = backend.load(f, "mmlx")
    proj.load(proj_data)

proj.render(f"{file}.wav")
