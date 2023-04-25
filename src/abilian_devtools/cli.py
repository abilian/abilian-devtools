# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.metadata

from cleez import CLI
from cleez.actions import VERSION


def main():
    cli = get_cli()
    cli.run()


def get_cli():
    version = importlib.metadata.version("abilian-devtools")
    cli = CLI(name="adt", version=version)
    cli.add_option(
        "-V",
        "--version",
        action=VERSION,
        version=cli.version,
        help="Show version and exit",
    )
    cli.add_option(
        "-d", "--debug", default=False, action="store_true", help="Enable debug mode"
    )
    cli.add_option(
        "-v", "--verbose", default=False, action="store_true", help="Increase verbosity"
    )
    cli.scan("abilian_devtools.commands")
    return cli
