# SPDX-FileCopyrightText: 2023 2022-2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import glob
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer()


def run(cmd):
    typer.secho(cmd, fg=typer.colors.GREEN)
    args = shlex.split(cmd)
    p = subprocess.Popen(args)
    p.wait()
    if p.returncode:
        typer.secho(f"failed with error code {p.returncode}", fg="red")
        # typer.secho(p.stderr)
        sys.exit()


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
    run("deptry .")


@app.command("security-check")
def security_check():
    """Run security checks."""
    run("pip-audit")
    run("safety check")

    # TODO: don't assume source dir is src
    # run("bandit -r src")


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


@app.callback()
def main():
    """Abilian Dev Tools command-line runner."""
    # Nothing here yet


if __name__ == "__main__":
    app()
