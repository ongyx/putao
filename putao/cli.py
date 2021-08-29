# coding: utf8

import functools
import logging
import pathlib
import shutil
import tempfile
import time

import click

from . import backend, utau
from .core import Config, Project
from .resamplers import RESAMPLERS

from .__version__ import __version__

click.option = functools.partial(click.option, show_default=True)  # type: ignore

EXT = "project.gz"


class Stopwatch:
    def __init__(self):
        self.start = 0

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *_, **__):
        end = time.time()
        click.echo(f"Elapsed time: {round(end - self.start, 2)}s")


class Checkbox:
    def __init__(self, choices):
        self.choices = choices
        self.picked = set()

    def show_choices(self):
        click.echo(
            "\n".join(
                "[{p}] {n}: {c} ".format(
                    p="x" if c in self.picked else " ", n=n, c=c.name
                )
                for n, c in enumerate(self.choices)
            )
        )

    def prompt(self, msg):
        self.picked.clear()

        click.echo(msg)

        while True:
            self.show_choices()
            pick = click.prompt("", "", show_default=False)

            if not pick:
                if self.picked:
                    break
                else:
                    click.echo("No choices made yet!")
                    continue

            index = int(pick)
            if not (0 <= index < len(self.choices)):
                click.echo("Invalid index!")
                continue

            choice = self.choices[index]
            if choice not in self.picked:
                self.picked.add(choice)
            else:
                self.picked.remove(choice)

        return self.picked


@click.group()
@click.version_option(__version__)
def cli():
    logging.basicConfig(level=logging.DEBUG)


@cli.command("extract")
@click.argument("zfile")
@click.option(
    "-t",
    "--target",
    default=".",
    help="where to extract the voicebank to",
    type=pathlib.Path,
)
def v_extract(zfile, target):
    """Extract the voicebank(s) in zfile."""

    with tempfile.TemporaryDirectory() as _tempdir:
        tempdir = pathlib.Path(_tempdir)

        # extract to tempdir first
        utau.extract(zfile, tempdir)

        # find all folders with an oto.ini file
        choices = [p.parent for p in tempdir.rglob(utau.CONFIG_FILE)]

        chosen = Checkbox(choices).prompt(
            (
                "Select voicebanks to extract.\n"
                "If more than one is selected, it will be appended into one voicebank.\n"
                "Once you are done selecting, press Enter."
            )
        )

        config = []

        for voicebank in chosen:
            for path in voicebank.iterdir():
                if path.name == "oto.ini":
                    config.append(path.read_text("utf8"))
                else:
                    shutil.move(str(path), str(target))

        (target / "oto.ini").write_text("\n".join(config), "UTF8")

    print("done")


def _p_new(name):
    click.echo(f"Creating new project '{name}'.")

    author = click.prompt("Author of project (your name)")

    voicebank = click.prompt("Path to UTAU voicebank")

    resampler = click.prompt(
        "Choose a resampler to use",
        type=click.Choice(list(RESAMPLERS)),
        default="world",
    )

    click.echo(f"Sucessfully created project '{name}'.")

    return Config(name, author, voicebank, resampler)


@cli.command("new")
@click.argument("name")
@click.option(
    "-o",
    "--output",
    help=f"where to save new project (defaults to curdir/(name).{EXT})",
)
def p_new(name, output):
    """Create a new project through an interactive wizard."""

    config = _p_new(name)
    config_path = output or pathlib.Path(".") / f"{name}.{EXT}"

    project = Project(config)
    project.dump(config_path)


@cli.command("import")
@click.argument("file")
@click.argument("proj_file")
@click.option(
    "-f",
    "--fmt",
    type=click.Choice(backend.BACKENDS),
    help="external file format",
)
def p_import(file, proj_file, fmt):
    """Import an external file into an existing project in proj_file."""

    file = pathlib.Path(file)

    if not fmt:
        # guess format using file extension
        fmt = file.suffix[1:]

    project = Project.load(proj_file)

    with file.open("rb") as f:
        backend.load(f, fmt, project)

    project.dump(proj_file)

    click.echo("done")


@cli.command("render")
@click.argument("proj_file")
@click.option("-o", "--output", default="render.wav", help="file to render to")
def p_render(proj_file, output):
    """Render a project file."""

    proj = Project.load(proj_file)

    with Stopwatch():
        proj.render(output)

    click.echo("done")
