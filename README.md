# 葡萄 (putao, grape): Poor man's UTAU

putao is a Python module that allows programmatic creation, editing, and saving of UTAU-style songs.

No more having to wrestle with encoding issues: all filenames use plain ASCII romanization of Japanese syllables!

Inspired by [Composite's](https://www.youtube.com/c/Composite1618) [Bad Apple](https://github.com/Composite1618/CompositeMemes/blob/main/bad%20apple.py) script.

## Why name it putao?

Because python + utau = putao. Conincidentally, it means 'grape' in Chinese.

## How it works

putao uses voicebanks, like a normal voice synthesizer.
A voicebank is a regular folder with wav files, and a `putao.json` config file that maps those wavs to syllables.

The syllables are then pitched using [scientific pitch notation](https://en.wikipedia.org/wiki/Scientific_pitch_notation) and streched according to a duration.
The result of this is a lyric. The lyrics can then be joined into a song.

## Making a song

Musical notes are written with [Music Macro Language](https://en.wikipedia.org/wiki/Music_Macro_Language) and mapped together with plaintext lyric files to create songs.

See the [examples](./examples) folder for what a voicebank and song should look like.

## Todo

- Add midi support
- GUI, like UTAU
- Project-like import/export (50%)

## Install

```
pip install putao
```

On Linux, you may have to install your distro's equivelent of the packages `libsndfile1` and `sox`.
i.e Debian:

```
sudo apt install libsndfile1 sox
```

## License

MIT.
