"""Version bumper, as an invoke task."""

from invoke import Context

from abilian_devtools.commands.bump import bump_version as _bump_version

TASKS = ["bump_version"]


def bump_version(c: Context, rule: str = "patch") -> None:
    """Bump version in pyproject.toml, commit & apply tag.

    Parameter "rule" can be one of: "daily", "patch", "minor", or
    "major". The same as `adt bump-version`.
    """
    _bump_version(rule)
