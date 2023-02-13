"""Version bumpers, using date-based versioning.

Todo: also support semantic versionning.
"""

import sys
from time import gmtime, strftime

import tomlkit
from invoke import Context

TASKS = ["bump_version"]


def bump_version(c: Context):
    """Bump version in pyproject.toml, commit & apply tag."""

    r = c.run("git diff --quiet", echo=True, warn=True)
    if r.exited != 0:
        print("git diff --quiet failed")
        sys.exit()

    update_version()
    c.run(f"git tag {get_version()}", echo=True)
    c.run("git add pyproject.toml", echo=True)
    c.run("git commit -m 'Bump version'", echo=True)


def update_version():
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
