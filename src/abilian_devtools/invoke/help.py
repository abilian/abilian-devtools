"""Reusable invoke tasks."""

from invoke import Context

from abilian_devtools.commands.help import help_make as _help_make

TASKS = ["help", "help_make"]


def help(c: Context):
    c.run("invoke --list")


def help_make(c: Context):
    """Helper to generate the `make help` message."""
    _help_make()
