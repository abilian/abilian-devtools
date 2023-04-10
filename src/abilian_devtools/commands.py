# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import glob
import shutil
from pathlib import Path

import typer

from .app import app, run

CRUFT_DIRS = [".mypy_cache", ".pytest_cache", ".ruff_cache"]


@app.command()
def all():
    """Run everything (linters and tests)."""
    check([])
    test([])


@app.command()
def test(args: list[str] = typer.Argument(None)):
    """Run tests."""
    if not args:
        args = ["src", "tests"]

    check_files_exist(args)

    args_str = " ".join(args)
    run(f"pytest {args_str}")


@app.command()
def check(args: list[str] = typer.Argument(None)):
    """Run checker/linters on specified files or directories."""
    if not args:
        args = ["src", "tests"]

    check_files_exist(args)

    args_str = " ".join(args)

    run(f"ruff {args_str}")
    run(f"flake8 {args_str}")
    run(f"mypy --show-error-codes {args_str}")
    run("pyright")
    run(f"vulture --min-confidence 80 {args_str}")
    # TODO: currently broken
    # run("deptry .")


@app.command()
def format(args: list[str] = typer.Argument(None)):
    """Format code in specified files or directories."""
    if not args:
        args = ["src", "tests"]

    check_files_exist(args)

    args_str = " ".join(args)

    run(f"black {args_str}")
    run(f"isort {args_str}")


def check_files_exist(args):
    for arg in args:
        if not Path(arg).exists():
            typer.secho(f"{arg} does not exist", fg=typer.colors.RED)
            raise typer.Exit(1)


@app.command("security-check")
def security_check(ctx: typer.Context):
    """Run security checks (deprecated, use 'audit' instead)."""
    typer.secho(
        "WARNING: 'security-check' is deprecated, use 'audit' instead.",
        fg=typer.colors.YELLOW,
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
def clean():
    """Cleanup cruft."""
    typer.secho(
        "Removing Python bytecode cache directories...", fg=typer.colors.BRIGHT_MAGENTA
    )
    for cache_dir in glob.glob("**/__pycache__", recursive=True):
        shutil.rmtree(cache_dir)

    typer.secho("Removing other caches...", fg=typer.colors.BRIGHT_MAGENTA)
    for cache_dir in CRUFT_DIRS:
        if Path(cache_dir).exists():
            typer.secho(f"Removing {cache_dir}", fg=typer.colors.YELLOW)
            shutil.rmtree(cache_dir, ignore_errors=True)
