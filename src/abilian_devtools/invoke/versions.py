"""Version bumpers, using date-based versioning.

Todo: also support semantic versionning.
"""

import sys
from time import gmtime, strftime

import tomlkit
from invoke import Context

TASKS = ["bump_version"]


def bump_version(c: Context, rule: str = "patch"):
    """Bump version in pyproject.toml, commit & apply tag.

    Parameter "rule" can be one of: "daily" or a parameter accepted by
    "poetry version".
    """
    r = c.run("git diff --quiet", echo=True, warn=True)
    if r.exited != 0:
        print("git diff --quiet failed")
        sys.exit()

    update_version(c, rule)
    version = get_version()
    c.run(f"git tag {version}", echo=True)
    c.run("git add pyproject.toml", echo=True)
    c.run(f"git commit -m 'Bump version ({version})'", echo=True)


def update_version(c, rule):
    if rule == "daily":
        update_version_daily(rule)
    else:
        c.run(f"poetry version {rule}", echo=True)


def update_version_daily(rule):
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
