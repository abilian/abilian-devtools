# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from cleez.command import Command

from .check import CheckCommand
from .test import TestCommand

CRUFT_DIRS = [".mypy_cache", ".pytest_cache", ".ruff_cache"]


class AllCommand(Command):
    """Run everything (linters and tests)."""

    name = "all"

    def run(self):
        CheckCommand(self.cli).run()
        TestCommand(self.cli).run()
