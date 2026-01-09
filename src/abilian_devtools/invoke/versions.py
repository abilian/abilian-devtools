"""Version bumpers, using date-based versioning.

Todo: also support semantic versionning.
"""

import sys

from invoke import Context

from abilian_devtools.commands.bump import Versionner

TASKS = ["bump_version"]


def bump_version(c: Context, rule: str = "patch"):
    """Bump version in pyproject.toml, commit & apply tag.

    Parameter "rule" can be one of: "daily", "patch", "minor", or
    "major".
    """
    r = c.run("git diff --quiet", echo=True, warn=True)
    if r.exited != 0:
        print("git diff --quiet failed")
        sys.exit()

    versionner = Versionner(rule)
    versionner.update_version()
    version = versionner.get_version()
    c.run("git add pyproject.toml", echo=True)
    c.run(f"git commit -m 'Bump version ({version})'", echo=True)
    c.run(f"git tag {version}", echo=True)
