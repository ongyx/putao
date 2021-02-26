# coding: utf8

import numpy as np

import soundfile

from putao import core

song = "megalovania"
notes = 44
# notes = 27

# create sine wave
y = np.sin(2 * np.pi * 440.0 * np.arange(core.SAMPLE_RATE * 1.0) / core.SAMPLE_RATE)

soundfile.write("sine.wav", y, core.SAMPLE_RATE)

lyrics = ["sine" for _ in range(notes)]

project = core.Project()
project.create([lyrics], open(f"{song}.mml", "rb").read(), "mml")
project.render(f"{song}.wav")
