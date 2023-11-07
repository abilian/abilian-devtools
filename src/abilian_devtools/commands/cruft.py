# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

import sys
from pathlib import Path

from cleez.command import Command

STD_FILES = [
    ".git/",
    ".gitignore",
    ".pre-commit-config.yaml",
    "Makefile",
    "README.md",
    # noxfile.py (or tox.ini)
    "poetry.lock",
    "pyproject.toml",
    "ruff.toml",
    "src/",
    "setup.cfg",
    "tests/",
]


class CruftCommand(Command):
    """Run cruft audit."""

    name = "cruft"

    def run(self):
        self.check_standard_files()

    def check_standard_files(self):
        """Check standard files ("cruft") are present."""
        success = True

        for std_file in STD_FILES:
            if not Path(std_file).exists():
                print(f"Missing standard file: {std_file}")
                success = False

        if not Path("tox.init").exists() and not Path("noxfile.py").exists():
            print("Missing tox.ini or noxfile.py")
            success = False

        if not success:
            sys.exit(1)
