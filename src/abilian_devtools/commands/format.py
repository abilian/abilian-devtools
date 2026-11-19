# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT


from cleez.colors import bold
from cleez.command import Argument, Command

from ..shell import run
from ._util import get_targets


class FormatCommand(Command):
    """Format code in specified files or directories."""

    name = "format"

    arguments = [
        Argument("args", nargs="*", help="Files or directories to format"),
    ]

    def run(self, args: list[str] | None = None) -> None:
        print(bold("Formatting code..."))

        targets = get_targets(args)
        run(["ruff", "format", *targets])
