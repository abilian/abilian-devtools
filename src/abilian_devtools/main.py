# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

import typer

# Import submodules to register their commands
from . import bumper, commands, help
from .app import app

assert bumper
assert help
assert commands


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Abilian Dev Tools command-line runner.

    Helps keeping your project clean and healthy.
    """
    if ctx.invoked_subcommand is None:
        ctx.get_help()
