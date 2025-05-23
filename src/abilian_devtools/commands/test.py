# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT


from cleez.colors import bold
from cleez.command import Argument, Command

from ..shell import run
from ._util import get_targets


class TestCommand(Command):
    """Run tests."""

    name = "test"

    arguments = [
        Argument("args", nargs="?", help="Files or directories to test"),
    ]

    def run(self, args: list[str] | None = None):
        print(bold("Running tests..."))

        args = get_targets(args)
        args_str = " ".join(args)

        run(f"pytest {args_str}")
