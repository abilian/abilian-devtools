# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import glob
import shutil
from pathlib import Path

import typer

from abilian_devtools.app import app, run

from . import bumper

assert bumper


@app.command()
def check(args: list[str]):
    """Run checker/linters on specified files or directories."""
    args2 = []
    for arg in args:
        if not Path(arg).exists():
            typer.secho(f"{arg} does not exist", fg=typer.colors.RED)
        else:
            args2.append(arg)

    args_str = " ".join(args2)

    run(f"ruff {args_str}")
    run(f"flake8 {args_str}")
    run(f"mypy --show-error-codes {args_str}")
    run("pyright")
    run(f"vulture --min-confidence 80 {args_str}")
    # TODO: currently broken
    # run("deptry .")


@app.command("security-check")
def security_check(ctx: typer.Context):
    """Run security checks (deprecated, use 'audit' instead)."""
    typer.secho(
        "WARNING: 'security-check' is deprecated, use 'audit' instead.",
        fg=typer.colors.RED,
    )
    ctx.invoke(audit)


@app.command()
def audit():
    """Run security audit."""
    run("pip-audit")
    # TODO: don't assume source dir is src
    run("bandit -q -c pyproject.toml -r src")
    # TODO: suppress output on success
    run("reuse lint")
    # TODO: Don't run safety check for now, it's too noisy
    # run("safety check")


@app.command()
def test():
    """Run tests."""
    run("pytest")


@app.command()
def all():
    """Run everything (linters and tests)."""
    check(["src", "tests"])
    test()


@app.command()
def clean():
    """Cleanup cruft."""
    typer.echo("Removing cache directories")
    for cache_dir in glob.glob("**/__pycache__", recursive=True):
        shutil.rmtree(cache_dir)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Abilian Dev Tools command-line runner.

    Helps keeping your project clean and healthy.
    """
    if ctx.invoked_subcommand is None:
        ctx.get_help()
