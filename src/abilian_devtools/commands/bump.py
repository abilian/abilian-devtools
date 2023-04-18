import sys
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
        Argument("rule", nargs="?", help="Bump rule"),
    ]

    def run(self, rule: str = "patch"):
        return_code = run("git diff --quiet", warn=True)
        if return_code != 0:
            print("Your repo is dirty. Please commit or stash changes first.")
            sys.exit(1)

        update_version(rule)
        version = get_version()
        run("git add pyproject.toml")
        run(f"git commit -m 'Bump version ({version})'")
        run(f"git tag {version}")


def update_version(rule):
    if rule == "daily":
        update_version_daily()
    else:
        run(f"poetry version {rule}")


def update_version_daily():
    pyproject_d = tomlkit.parse(open("pyproject.toml").read())
    version: str = pyproject_d["tool"]["poetry"]["version"]  # type: ignore
    serial = int(version.split(".")[-1])
    date = version[: -len(str(serial)) - 1]

    new_date = strftime("%Y.%m.%d", gmtime())
    if date == new_date:
        serial += 1
    else:
        serial = 1

    new_version = f"{new_date}.{serial}"
    print("New version: ", new_version)
    pyproject_d["tool"]["poetry"]["version"] = new_version  # type: ignore
    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject_d))


def get_version():
    d = tomlkit.parse(open("pyproject.toml").read())
    version: str = d["tool"]["poetry"]["version"]  # type: ignore
    return version
