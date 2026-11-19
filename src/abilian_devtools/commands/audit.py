# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from cleez.command import Command

from ..shell import run


class AuditCommand(Command):
    """Run security audit."""

    name = "audit"

    def run(self) -> None:
        run(["pip-audit"])
        run(["bandit", "-q", "-c", "pyproject.toml", "-r", "src"])
        run(["reuse", "lint"])
