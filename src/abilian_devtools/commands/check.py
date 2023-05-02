# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
from pathlib import Path
from typing import Optional

from cleez.colors import bold
from cleez.command import Argument, Command

from ..shell import run
from ._util import check_files_exist


class CheckCommand(Command):
    """Run checker/linters on specified files or directories."""

    name = "check"

    arguments = [
        Argument("args", nargs="*", help="Files or directories to check"),
    ]

    def run(self, args: Optional[list[str]] = None):
        print(bold("Running checks..."))
        if not args:
            args = ["src", "tests"]

        check_files_exist(args)

        args_str = " ".join(args)

        # Todo: more cases
        if Path("etc").joinpath("ruff.toml").exists():
            run(f"ruff lint -c etc/ruff.toml {args_str}")
        else:
            run(f"ruff {args_str}")

        run(f"flake8 {args_str}")
        run(f"mypy --show-error-codes {args_str}")
        run("pyright")
        run(f"vulture --min-confidence 80 {args_str}")
        # TODO: currently broken
        # run("deptry .")
