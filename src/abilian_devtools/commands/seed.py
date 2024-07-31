# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import inspect
from pathlib import Path
from typing import Optional

from cleez.colors import bold
from cleez.command import Command

IGNORED_FILES = {
    "__pycache__",
    "__init__.py",
}


class SeedCommand(Command):
    """Seed project (add useful config files)."""

    name = "seed"

    def run(self, args: Optional[list[str]] = None):
        print(bold("Seeding project..."))

        etc_root = get_package_root("abilian_devtools") / "etc"
        for file in etc_root.iterdir():
            name = file.name
            if name in IGNORED_FILES:
                continue

            self.add_file(file)

    def add_file(self, file):
        name = file.name
        metadata = self.get_metadata(file)
        name = metadata.get("name", name)
        if Path(name).exists():
            print(f"{name} already exists")
            return
        print(f"Adding {name}...")
        content = file.read_text()
        Path(name).write_text(content)

    def get_metadata(self, file):
        metadata = {}
        content = file.read_text()
        lines = content.splitlines()
        for line in lines:
            if "ADT:" not in line:
                continue
            key, value = line.split("ADT:")[1].split("=", 1)
            metadata[key.strip()] = value.strip()
        return metadata


def get_package_root(package_name):
    module = __import__(package_name)
    package_path = inspect.getfile(module)
    return Path(package_path).parent
