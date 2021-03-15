# coding: utf8

import numpy as np

import soundfile

from putao import core

song = "megalovania"

# create sine wave
y = np.sin(2 * np.pi * 440.0 * np.arange(core.SAMPLE_RATE * 1.0) / core.SAMPLE_RATE)

soundfile.write("sine.wav", y, core.SAMPLE_RATE)

project = core.Project()
project.create(open(f"{song}.mml", "rb").read(), "mmlx")
project.render(f"{song}.wav")

# with open(f"{song}.json", "w") as f:
#    project.dump(f)
