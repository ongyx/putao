# coding: utf8

import numpy as np

import soundfile

from putao import core

song = "unravel"

# create sine wave
y = np.sin(2 * np.pi * 440.0 * np.arange(core.SAMPLE_RATE * 1.0) / core.SAMPLE_RATE)

soundfile.write("sine.wav", y, core.SAMPLE_RATE)

# lyrics = {"0": ["sine" for _ in range(notes)]}
lyrics = None

project = core.Project("morshu")
project.create(open(f"{song}.mml", "rb").read(), "mml", lyrics)
project.render(f"{song}.wav")

with open("test.json", "w") as f:
    project.dump(f)
