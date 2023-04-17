# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib.metadata

from cleez import CLI


# Quick hack for now
class MyCli(CLI):
    """Abilian Dev Tools command-line runner.

    Helps keeping your project clean and healthy.
    """

    def get_version(self):
        return importlib.metadata.version("abilian_devtools")


def main():
    cli = MyCli(name="adt")
    cli.add_option(
        "-h", "--help", default=False, action="store_true", help="Show help and exit"
    )
    cli.add_option(
        "-V",
        "--version",
        default=False,
        action="store_true",
        help="Show version and exit",
    )
    cli.add_option(
        "-d", "--debug", default=False, action="store_true", help="Enable debug mode"
    )
    cli.add_option(
        "-v", "--verbose", default=False, action="store_true", help="Increase verbosity"
    )
    cli.scan("abilian_devtools.commands")
    cli.run()


if __name__ == "__main__":
    main()
