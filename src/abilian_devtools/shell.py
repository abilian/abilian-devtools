# SPDX-FileCopyrightText: 2023-2026 2022-2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import shlex
import subprocess
import sys
from collections.abc import Sequence

from cleez.colors import dim, red


def run(args: Sequence[str], *, echo: bool = True, warn: bool = False) -> int:
    """Run a program, its arguments given as a list (no shell, no re-splitting).

    On failure, exit with the program's status, unless `warn` is set: then
    return the status for the caller to act on.
    """
    if echo:
        print(dim("> " + shlex.join(args)))
    returncode = subprocess.run(args, check=False).returncode
    if returncode and not warn:
        print(red(f"{args[0]} failed with exit status {returncode}"))
        sys.exit(returncode)
    return returncode
