# coding: utf8

import numpy as np

import soundfile

from putao import core

# create sine wave
sample_rate = 44100
y = np.sin(2 * np.pi * 440.0 * np.arange(sample_rate * 1.0) / sample_rate)

soundfile.write("sine.wav", y, sample_rate)

lyrics = ["sine" for _ in range(11 * 4)]

project = core.Project()
project.create(lyrics, open("megalovania.mml", "rb").read(), "mml")
project.render("megalovania.wav")
