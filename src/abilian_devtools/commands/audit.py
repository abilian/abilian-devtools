# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from cleez.command import Command

from ..shell import run


class AuditCommand(Command):
    """Run security audit."""

    name = "audit"

    def run(self):
        run("pip-audit")
        # TODO: don't assume source dir is src
        run("bandit -q -c pyproject.toml -r src")
        # TODO: suppress output on success
        run("reuse lint")
        # TODO: Don't run safety check for now, it's too noisy
        # run("safety check")
