# coding: utf8

import numpy as np

import soundfile

import putao


# create sine wave
sample_rate = 44100
y = np.sin(2 * np.pi * 440.0 * np.arange(sample_rate * 1.0) / sample_rate)

soundfile.write("sine.wav", y, sample_rate)

song = putao.Song.from_file("megalovania.txt", voicebank=".")

song.render("./test.wav")
