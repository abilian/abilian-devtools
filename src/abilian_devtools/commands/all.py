# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from cleez.command import Command

from .check import CheckCommand
from .test import TestCommand


class AllCommand(Command):
    """Run everything (linters and tests)."""

    name = "all"

    def run(self) -> None:
        CheckCommand(self.cli).run()
        TestCommand(self.cli).run()
