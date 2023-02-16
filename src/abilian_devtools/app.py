# SPDX-FileCopyrightText: 2023 2022-2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import shlex
import subprocess
import sys

import typer

app = typer.Typer()


def run(cmd, echo=True, warn=False):
    if echo:
        typer.secho("> " + cmd, fg=typer.colors.GREEN)
    args = shlex.split(cmd)
    p = subprocess.Popen(args)
    p.wait()
    if not warn and p.returncode:
        typer.secho(f"failed with error code {p.returncode}", fg="red")
        # typer.secho(p.stderr)
        sys.exit()
    return p.returncode
