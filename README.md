# putao (葡萄) 🍇

![レロレロ](https://github.com/ongyx/putao/blob/main/logo.png?raw=true)

Concatenative synthesizer inspired by UTAU.

Originally, it was a joke inspired by [Composite]'s [Bad Apple] script but is now an experimental attempt at creating a voice synthesizer in Python.

## About

putao uses UTAU voicebanks and UTAU Sequence Texts (USTs) for voice samples and song data.
The key difference is that putao does not shell out to `resampler.exe`,
or any other `.exe` compiled resampler/wavtool,
to ensure that it can be used cross-platform.

putao is able to detect encoding as well, allowing the use of both Shift-JIS and UTF-8 voicebanks.

## Installation

putao requires Python 3.11 or later to run.

```
pip install putao
```

## License

MIT.

[Composite]: https://www.youtube.com/c/Composite1618
[Bad Apple]: https://github.com/Composite1618/CompositeMemes/
[pyworld]: https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder
[librosa]: https://github.com/librosa/librosa
