import sys

from cleez import Argument, Command

from ..bumper import get_version, update_version
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
