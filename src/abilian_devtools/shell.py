# SPDX-FileCopyrightText: 2023 2022-2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
import shlex
import subprocess
import sys

from cleez.colors import dim, red


def run(cmd, echo=True, warn=False):
    if echo:
        print(dim("> " + cmd))
    args = shlex.split(cmd)
    p = subprocess.Popen(args)
    p.wait()
    if not warn and p.returncode:
        print(red(f"failed with error code {p.returncode}"))
        sys.exit()
    return p.returncode
