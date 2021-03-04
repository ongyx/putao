# coding: utf8

import tempfile

import numpy as np
import soundfile
import sox

sample_to_tune = "morshu/o.wav"


y, sr = soundfile.read(sample_to_tune)
# middle C, C4
a_sine_wave = np.sin(2 * np.pi * 261.625565 * np.arange(sr * 1.0) / sr)


with tempfile.NamedTemporaryFile(suffix=".wav") as tf:
    soundfile.write(tf, a_sine_wave, sr)

    cbn = sox.Combiner()
    cbn.build([tf.name, sample_to_tune], "morshu/o_.wav", "multiply")
