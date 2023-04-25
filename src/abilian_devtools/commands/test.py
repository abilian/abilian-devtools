# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from typing import Optional

from cleez.colors import bold
from cleez.command import Argument, Command

from ..shell import run
from ._util import check_files_exist


class TestCommand(Command):
    """Run tests."""

    name = "test"

    arguments = [
        Argument("args", nargs="?", help="Files or directories to test"),
    ]

    def run(self, args: Optional[list[str]] = None):
        print(bold("Running tests..."))
        if not args:
            args = ["src", "tests"]

        check_files_exist(args)

        args_str = " ".join(args)
        run(f"pytest {args_str}")
