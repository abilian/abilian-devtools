"""Version bumpers, using date-based versioning.

Todo: also support semantic versionning.
"""

import sys

from invoke import Context

from abilian_devtools.commands.bump import get_version, update_version

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

    update_version(rule)
    version = get_version()
    c.run(f"git tag {version}", echo=True)
    c.run("git add pyproject.toml", echo=True)
    c.run(f"git commit -m 'Bump version ({version})'", echo=True)
