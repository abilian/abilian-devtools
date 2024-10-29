import sys
from pathlib import Path
from time import gmtime, strftime

import tomlkit
from cleez import Argument, Command

from ..shell import run


class BumpVersionCommand(Command):
    """Bump version in pyproject.toml, commit & apply tag.

    Parameter "rule" can be one of: "daily" or a parameter accepted by
    "poetry version".
    """

    name = "bump-version"
    help = "Bump version in pyproject.toml, commit & apply tag."

    arguments = [
        Argument(
            "rule",
            nargs="?",
            default="patch",
            help="Bump rule (patch, minor, major, daily)",
        ),
    ]

    def run(self, rule: str = "patch"):
        return_code = run("git diff --quiet", warn=True)
        if return_code != 0:
            print("Your repo is dirty. Please commit or stash changes first.")
            sys.exit(1)

        versionner = Versionner(rule)
        versionner.update_version()
        version = versionner.get_version()

        run("git add pyproject.toml")
        run(f"git commit -m 'Bump version ({version})'")
        run(f"git tag {version}")


class Versionner:
    rule: str
    pyproject: tomlkit.document

    def __init__(self, rule: str):
        # NB: we're using tomlkit for its roundtrip feature.
        self.pyproject = tomlkit.parse(Path("pyproject.toml").read_text())
        self.rule = rule

    def read_pyproject(self):
        self.pyproject = tomlkit.parse(Path("pyproject.toml").read_text())

    def write_pyproject(self):
        Path("pyproject.toml").write_text(tomlkit.dumps(self.pyproject))

    def get_version(self):
        if "tool" in self.pyproject and "poetry" in self.pyproject["tool"]:
            version: str = self.pyproject["tool"]["poetry"]["version"]  # type: ignore
        else:
            version = self.pyproject["project"]["version"]

        return version

    def set_version(self, version: str):
        if "tool" in self.pyproject and "poetry" in self.pyproject["tool"]:
            self.pyproject["tool"]["poetry"]["version"] = version
        else:
            self.pyproject["project"]["version"] = version

    def update_version(self):
        if self.rule == "daily":
            new_version = self.new_version_daily()
        else:
            new_version = self.new_version()

        print("New version: ", new_version)
        self.set_version(new_version)
        self.write_pyproject()

    def new_version_daily(self):
        version = self.get_version()

        serial = int(version.split(".")[-1])
        date = version[: -len(str(serial)) - 1]

        new_date = strftime("%Y.%m.%d", gmtime())
        if date == new_date:
            serial += 1
        else:
            serial = 1

        new_version = f"{new_date}.{serial}"
        return new_version

    def new_version(self):
        version = self.get_version()
        major, minor, patch = version.split(".")
        match self.rule:
            case "major":
                major = str(int(major) + 1)
                minor = "0"
                patch = "0"
            case "minor":
                minor = str(int(minor) + 1)
                patch = "0"
            case "patch":
                patch = str(int(patch) + 1)
            case _:
                raise ValueError(f"Unknown rule: {self.rule}")
        new_version = f"{major}.{minor}.{patch}"
        return new_version
