Abilian Development Tools
=========================

What this is?
-------------

This is a curated, and opiniated, collection of best-of-breed Python development tools:

- Formatters (`black`, `isort`, `docformatter`)
- Testing frameworks (`pytest` and friends, `nox`)
- Style checkers (`ruff`, `flake8` and friends)
- Type checkers (`mypy`, `pyright`)
- Supply chain audit (`pip-audit`, `safety`, `reuse`, `vulture`, `deptry`)
- And more.

Usage
-----

You still need to properly configure and call them in your own projects.

For example configuration, see, for instance, <https://github.com/abilian/nua> (`Makefile`, `pyproject.toml`, `setup.cfg`).

We're providing a CLI called `adt`,

```
$ adt --help
Usage: adt [OPTIONS] COMMAND [ARGS]...

Abilian Dev Tool command-line runner.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --install-completion        [bash|zsh|fish|powershe  Install completion for  │
│                             ll|pwsh]                 the specified shell.    │
│                                                      [default: None]         │
│ --show-completion           [bash|zsh|fish|powershe  Show completion for the │
│                             ll|pwsh]                 specified shell, to     │
│                                                      copy it or customize    │
│                                                      the installation.       │
│                                                      [default: None]         │
│ --help                                               Show this message and   │
│                                                      exit.                   │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ all      Run everything.                                                     │
│ check    Run checker/linters on specified files or directories.              │
│ test     Run tests.                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```