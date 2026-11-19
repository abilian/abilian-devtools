# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
from pathlib import Path

from cleez.colors import bold
from cleez.command import Argument, Command

from ..shell import run
from ._util import get_targets


class CheckCommand(Command):
    """Run checker/linters on specified files or directories."""

    name = "check"

    arguments = [
        Argument("args", nargs="*", help="Files or directories to check"),
    ]

    def run(self, args: list[str] | None = None) -> None:
        print(bold("Running checks..."))

        targets = get_targets(args)

        if Path("etc").joinpath("ruff.toml").exists():
            run(["ruff", "check", "-c", "etc/ruff.toml", *targets])
        else:
            run(["ruff", "check", *targets])

        run(["vulture", "--min-confidence", "80", *targets])
