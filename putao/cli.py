# coding: utf8

import functools
import json
import logging
import pathlib
import shutil
import tempfile
import time

import click

from . import core, backend, model, utau
from .__version__ import __version__

click.option = functools.partial(click.option, show_default=True)  # type: ignore

EXT = "project"


class Stopwatch:
    def __init__(self):
        self.start = 0

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *_, **__):
        end = time.time()
        click.echo(f"Elapsed time: {round(end - self.start, 2)}s")


@click.group()
@click.version_option(__version__)
def cli():
    logging.basicConfig(level=logging.DEBUG)


@cli.command("extract")
@click.argument("zfile")
@click.option("-t", "--target", default=".", help="where to extract the voicebank to")
def v_extract(zfile, target):
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


def _p_new(name):
    click.echo(f"Creating new project '{name}'.")

    author = click.prompt("Author of project (your name)")

    voicebank = click.prompt("Path to UTAU voicebank")

    resampler = click.prompt(
        "Choose a resampler to use",
        type=click.Choice(list(model.RESAMPLERS)),
        default="WorldResampler",
    )

    click.echo(f"Sucessfully created project '{name}'.")

    return {
        "name": name,
        "author": author,
        "voicebank": voicebank,
        "resampler": resampler,
        "putao_version": __version__,
    }


@cli.command("new")
@click.argument("name")
@click.option(
    "-o", "--output", help="where to save new project (defaults to curdir/(name).json)"
)
def p_new(name, output):
    """Create a new project through an interactive wizard."""

    config = _p_new(name)
    config_path = output or pathlib.Path(".") / f"{name}.{EXT}"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


@cli.command("import")
@click.argument("file")
@click.argument("proj_file")
@click.option(
    "-f",
    "--fmt",
    type=click.Choice(backend.BACKENDS),
    help="external file format",
)
@click.option("-l", "--lyric_file", help="override phonemes in the external file")
def p_import(file, proj_file, fmt, lyric_file):
    """Import an external file into an existing project in proj_file."""

    file = pathlib.Path(file)

    if not fmt:
        # guess format using file extension
        fmt = file.suffix[1:]

    config = json.load(open(proj_file))

    with file.open("rb") as f:
        config["tracks"] = backend.load(f, fmt)

    if lyric_file:
        counter = 0
        with open(lyric_file) as f:
            for line in f.splitlines():
                for phoneme in line.split():

                    note = config["tracks"]["lead"][count]

                    if not phoneme or note.type != "note":
                        continue

                    config["tracks"]["lead"][count]["phoneme"] = phoneme

                    count += 1

    with open(proj_file, "w") as f:
        json.dump(config, f, indent=4)

    click.echo("done")


@cli.command("frq")
@click.argument("proj_file")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="regenerate frq files even if they already exist",
)
def p_frq(proj_file, force):
    """Generate frq files for a project using its renderer."""

    proj = core.Project.load(proj_file)

    if "frq" not in proj.config or force:
        click.echo(
            f"generating frq files using {proj.resampler.name}, this might take a while..."
        )
        proj.resampler.gen_frq_all(force=force)
        proj.config["frq"] = True
        proj.dump(proj_file)

    click.echo("done")


@cli.command("render")
@click.argument("proj_file")
@click.option("-o", "--output", default="render.wav", help="file to render to")
def p_render(proj_file, output):
    """Render a project file."""

    proj = core.Project.load(proj_file)

    with Stopwatch():
        proj.render(output)

    click.echo("done")
