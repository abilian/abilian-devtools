# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import shutil
from pathlib import Path

from cleez.colors import bold, dim
from cleez.command import Command

CRUFT_DIRS = [".mypy_cache", ".pytest_cache", ".ruff_cache"]


class CleanCommand(Command):
    """Cleanup cruft."""

    name = "clean"

    def run(self):
        print(bold("Removing Python bytecode cache directories..."))
        for cache_dir in Path().rglob("**/__pycache__"):
            shutil.rmtree(cache_dir)

        print(bold("Removing other caches..."))
        for cache_dir in CRUFT_DIRS:
            if Path(cache_dir).exists():
                print(dim(f"Removing {cache_dir}"))
                shutil.rmtree(cache_dir, ignore_errors=True)
