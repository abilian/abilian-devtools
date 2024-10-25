# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from typing import Optional

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

    def run(self, args: Optional[list[str]] = None):
        print(bold("Formatting code..."))

        args = get_targets(args)
        args_str = " ".join(args)

        run(f"black {args_str}")
        run(f"isort {args_str}")
