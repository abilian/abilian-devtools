# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import glob
import shutil
from pathlib import Path

from cleez.colors import bold, dim, red
from cleez.command import Argument, Command

from ..shell import run

CRUFT_DIRS = [".mypy_cache", ".pytest_cache", ".ruff_cache"]


class AllCommand(Command):
    """Run everything (linters and tests)."""

    name = "all"

    def run(self):
        CheckCommand(self.cli).run()
        TestCommand(self.cli).run()


class TestCommand(Command):
    """Run tests."""

    name = "test"

    arguments = [
        Argument("args", nargs="?", help="Files or directories to test"),
    ]

    def run(self, args: list[str] = None):
        print(bold("Running tests..."))
        if not args:
            args = ["src", "tests"]

        check_files_exist(args)

        args_str = " ".join(args)
        run(f"pytest {args_str}")


class CheckCommand(Command):
    """Run checker/linters on specified files or directories."""

    name = "check"

    arguments = [
        Argument("args", nargs="*", help="Files or directories to check"),
    ]

    def run(self, args: list[str] = None):
        print(bold("Running checks..."))
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


class FormatCommand(Command):
    """Format code in specified files or directories."""

    name = "format"

    arguments = [
        Argument("args", nargs="*", help="Files or directories to format"),
    ]

    def run(self, args: list[str] = None):
        print(bold("Formatting code..."))
        if not args:
            args = ["src", "tests"]

        check_files_exist(args)

        args_str = " ".join(args)

        run(f"black {args_str}")
        run(f"isort {args_str}")


def check_files_exist(args):
    for arg in args:
        if not Path(arg).exists():
            print(red(f"{arg} does not exist"))
            raise SystemExit(1)


class AuditCommand(Command):
    """Run security audit."""

    name = "audit"

    def run(self):
        run("pip-audit")
        # TODO: don't assume source dir is src
        run("bandit -q -c pyproject.toml -r src")
        # TODO: suppress output on success
        run("reuse lint")
        # TODO: Don't run safety check for now, it's too noisy
        # run("safety check")


class CleanCommand(Command):
    """Cleanup cruft."""

    name = "clean"

    def run(self):
        print(bold("Removing Python bytecode cache directories..."))
        for cache_dir in glob.glob("**/__pycache__", recursive=True):
            shutil.rmtree(cache_dir)

        print(bold("Removing other caches..."))
        for cache_dir in CRUFT_DIRS:
            if Path(cache_dir).exists():
                print(dim(f"Removing {cache_dir}"))
                shutil.rmtree(cache_dir, ignore_errors=True)
