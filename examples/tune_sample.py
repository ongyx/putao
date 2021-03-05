# coding: utf8

import tempfile

import numpy as np
import soundfile
import sox


cbn = sox.Combiner()
cbn.build(["morshu/prod/a4_long.wav", "morshu/prod/morshu.wav"], "test.wav", "merge")
