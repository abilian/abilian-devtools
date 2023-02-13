"""
Experimental: reusable invoke tasks.
"""
import re
from pathlib import Path

from invoke import Context

TASKS = ["help", "help_make"]


def help(c: Context):
    c.run("invoke --list")


def help_make(c: Context):
    """Helper to generate the `make help` message."""
    # TODO: should try harder to find the right file
    with Path("Makefile").open() as f:
        makefile = f.read()

    targets = MakefileParser().parse(makefile)

    max_len = max(len(t[0]) for t in targets)

    print("Targets:\n")
    for targets, description in targets:
        print(f"{targets:<{max_len}}  {description}")


class MakefileParser:
    def __init__(self):
        self.target = ""
        self.description = ""
        self.targets = []

    def parse(self, makefile: str):
        for line in makefile.splitlines():
            self.parse_line(line)
        return self.targets

    def parse_line(self, line: str):
        if m := re.match(r"^## (.*)", line):
            self.description = m.group(1)
        elif m := re.match("^(.*?):", line):
            self.target = m.group(1)
            if self.description:
                self.targets.append([self.target, self.description])
        else:
            self.target = ""
            self.description = ""
