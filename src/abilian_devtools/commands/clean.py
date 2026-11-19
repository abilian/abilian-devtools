# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import os
import shutil
from pathlib import Path

from cleez.colors import bold, dim
from cleez.command import Command

CRUFT_DIRS = [".mypy_cache", ".pytest_cache", ".ruff_cache"]


class CleanCommand(Command):
    """Cleanup cruft."""

    name = "clean"

    def run(self) -> None:
        print(bold("Removing Python bytecode cache directories..."))
        for cache_dir in find_pycache_dirs(Path()):
            shutil.rmtree(cache_dir)

        print(bold("Removing other caches..."))
        for cache_dir in CRUFT_DIRS:
            if Path(cache_dir).exists():
                print(dim(f"Removing {cache_dir}"))
                shutil.rmtree(cache_dir, ignore_errors=True)


def find_pycache_dirs(root: Path) -> list[Path]:
    """The `__pycache__` directories under `root`, outside hidden directories
    (`.venv`, `.git`, `.nox`...), which are not the project's to clean."""
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        if "__pycache__" in dirnames:
            found.append(Path(dirpath) / "__pycache__")
        dirnames[:] = [
            d for d in dirnames if d != "__pycache__" and not d.startswith(".")
        ]
    return found
