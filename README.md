# putao (葡萄): Poor man's UTAU 🍇

putao is a Python module that allows programmatic creation, editing, and saving of UTAU-style songs.

No more having to wrestle with encoding issues: all filenames and text files use UTF-8, re-encoded from Shift-JIS if necessary.

Originally, it was a joke inspired by [Composite]'s [Bad Apple] script but is now an experimental attempt at creating a voice synthesizer in Python.

(Just kidding. Since putao now uses [pyworld] to pitch notes, it is now a JoJoke.)

## Why name it putao?

Because python + utau = putao. Conincidentally, it means 'grape' in Chinese.

## How it works

putao uses UTAU-format voicebanks (with `oto.ini` files).
Currently, pitch auto-detection is still WIP, so the pitch must still be manually specified.

The key difference is that putao does not shell out to `resampler.exe`, or any other `.exe` compiled resampler.
putao's resampler is written entierly in Python, thanks to [pyworld].

The resampler putao uses is divided into two parts:
`Note` and `Rest` in [`internals.py`](./putao/internals.py), which do most of the heavy lifting (pitching/clipping/looping phonemes),
and `Track` and `Project` in [`core.py`](./putao/core.py), which cobbles together the rendered notes and rests into a semi-coherent song.

To save time, putao generates analysis files from pyworld for all the wavfiles in `oto.ini`, similar to `.frq` files generated by UTAU's `resampler.exe`.
These analysis files are just numpy arrays saved in numpy's native format (hence the `.npy` extension).

Later on when rendering songs, the analysis can be loaded back into the resampler without have to analyse the wavfiles again.

## Making a song

Musical notes are written with an extended form of [Music Macro Language] to create songs.

Creating a GUI to make songs is currently high priority, and it will be worked on once putao's API is stabilised.

See the [examples](./examples) folder for what a voicebank and song should look like.

## Todo

- Add midi support (WIP)
- GUI

## Install

```
pip install putao
```

On Linux, you may have to install your distro's equivelent of the packages `libsndfile1`.
i.e Debian:

```
sudo apt install libsndfile1
```

## License

MIT.


[Composite]: https://www.youtube.com/c/Composite1618
[Bad Apple]: https://github.com/Composite1618/CompositeMemes/
[pyworld]: https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder
[Music Macro Language]: https://en.wikipedia.org/wiki/Music_Macro_Language
