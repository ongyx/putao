# coding: utf8

import functools
import logging
import pathlib
import shutil
import tempfile

import click

from putao import core, utau
from putao.__version__ import __version__

click.option = functools.partial(click.option, show_default=True)  # type: ignore


@click.group()
@click.version_option(__version__)
def cli():
    logging.basicConfig(level=logging.DEBUG)


@cli.group()
def voicebank():
    """Voicebank-related utils."""


@voicebank.command()
@click.argument("zfile")
@click.option("-t", "--target", default=".", help="where to extract the voicebank to")
def extract(zfile, target):
    """Extract the voicebank(s) in zfile."""

    with tempfile.TemporaryDirectory() as _tempdir:
        tempdir = pathlib.Path(_tempdir)

        # extract to tempdir first
        utau.extract(zfile, tempdir)

        # find all folders with an oto.ini file
        voicebanks = [p.parent for p in tempdir.rglob(utau.CONFIG_FILE)]
        for count, voicebank in enumerate(voicebanks):
            print(f"{count}: {voicebank.name}")

        choice = click.prompt("Voicebank to use", 0)
        voicebank_to_move = voicebanks[choice]

        for path in voicebank_to_move.iterdir():
            shutil.move(path, target)

    print("done")


@voicebank.command()
@click.argument("path")
@click.option("-f", "--force", default=False, is_flag=True, help="ignore existing frqs")
def frq(path, force):
    """Generate frequency files for a UTAU voicebank at path."""

    # pitch will not be used anyway.
    voicebank = utau.Voicebank(path, 0)
    voicebank.generate_frq(force=force)
