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
    """Helper to generate the `make help` message"""
    # TODO: should try harder to find the right file
    with Path("Makefile").open() as f:
        makefile = f.read()

    target = ""
    description = ""
    targets = []
    for line in makefile.splitlines():
        if m := re.match(r"^## (.*)", line):
            description = m.group(1)
        elif m := re.match("^(.*?):", line):
            target = m.group(1)
            if description:
                targets.append([target, description])
        else:
            target = ""
            description = ""

    max_len = max(len(t[0]) for t in targets)

    print("Targets:\n")
    for targets, description in targets:
        print(f"{targets:<{max_len}}  {description}")
