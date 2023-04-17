"""Version bumper."""

from time import gmtime, strftime

import tomlkit

from .shell import run


def update_version(rule):
    if rule == "daily":
        update_version_daily(rule)
    else:
        run(f"poetry version {rule}")


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
