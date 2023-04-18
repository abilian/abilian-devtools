# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
from pathlib import Path

from cleez.colors import red


def check_files_exist(args):
    for arg in args:
        if not Path(arg).exists():
            print(red(f"{arg} does not exist"))
            raise SystemExit(1)
