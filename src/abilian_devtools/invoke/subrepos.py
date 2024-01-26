"""Invoke tasks for subrepos.

Should be used at a higher level, e.g. for constructing "subrepos"
tasks.
"""

from collections.abc import Sequence

from cleez.colors import bold
from invoke import Context


def h1(msg: str):
    print(bold(msg))


def run_in_subrepos(c: Context, cmd: str, sub_repos: Sequence[str] = ()):
    for sub_repo in sub_repos:
        h1(f"Running '{cmd}' in subrepos: {sub_repo}")
        with c.cd(sub_repo):
            c.run(cmd, echo=True)
