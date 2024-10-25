# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
from pathlib import Path

from cleez.colors import red


def get_targets(args: None | list[str]) -> list[str]:
    if args:
        _check_files_exist(args)
        return args

    args = []
    if Path("src").exists():
        args.append("src")
    if Path("tests").exists():
        args.append("tests")
    return args


def _check_files_exist(args: list[str]) -> None:
    for arg in args:
        if not Path(arg).exists():
            print(red(f"{arg} does not exist"))
            raise SystemExit(1)
