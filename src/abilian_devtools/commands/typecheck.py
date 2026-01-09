# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from cleez.colors import bold
from cleez.command import Argument, Command

from ..shell import run
from ._util import get_targets


class TypeCheckCommand(Command):
    """Run type checker on specified files or directories."""

    name = "typecheck"

    arguments = [
        Argument("args", nargs="*", help="Files or directories to check"),
    ]

    def run(self, args: list[str] | None = None):
        print(bold("Running type checker..."))

        args = get_targets(args)
        args_str = " ".join(args)

        run(f"ty check {args_str}")
