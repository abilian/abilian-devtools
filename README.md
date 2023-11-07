Abilian Development Tools (`abilian-devtools` or `adt`)
=======================================================

Abilian Development Tools (ADT) is a curated collection of Python development tools that includes formatters, testing frameworks, style checkers, type checkers, and supply chain audit tools. By adding `abilian-devtools = '*'` to your project's `requirements.in` or `pyproject.toml`, you can access over 40+ curated projects and plugins.
Proper configuration and usage in your project is still required.
Additionally, the package provides a command-line interface (CLI) called adt to help users get started with various development tasks such as running tests, security audits, and code formatting.
ADT was developped at [Abilian](https://abilian.com/) as a tool to help manage dozens of Python projects (open source or not). We hope it can be useful to others too.


What this is?
-------------

This is a curated, and opiniated, collection of best-of-breed Python development tools:

- Formatters (`black`, `isort`, `docformatter`)
- Testing frameworks (`pytest` and friends, `nox`)
- Style checkers (`ruff`, `flake8` and friends)
- Type checkers (`mypy`, `pyright`)
- Supply chain audit (`pip-audit`, `safety`, `reuse`, `vulture`, `deptry`)
- And more.

Obviously, all the credit goes to the creators and maintainers of these wonderful projects. You have all our gratitude!


Usage
-----

Instead of having to track all the 40+ projects and plugins we have curated, you just need to add `abilian-devtools = '*'` in your project's `requirements.in` or `pyproject.toml`.

You still need to properly configure and call them in your own projects.

For example configuration, see, for instance, <https://github.com/abilian/nua> (`Makefile`, `pyproject.toml`, `setup.cfg`, `tasks.py`, `noxfile.py`...).


CLI helper
----------

As a bonus, we're providing a CLI called `adt` which can help you get started:

```
$ adt
adt (0.5.x)

Usage:
  adt <command> [options] [arguments]

Options:
  -V  Show version and exit
  -d  Enable debug mode
  -v  Increase verbosity

Available commands:
  all           Run everything (linters and tests).
  audit         Run security audit.
  bump-version  Bump version in pyproject.toml, commit & apply tag.
  check         Run checker/linters on specified files or directories.
  clean         Cleanup cruft.
  cruft         Run cruft audit.
  format        Format code in specified files or directories.
  help-make     Helper to generate the `make help` message.
  test          Run tests.
```


Why this?
---------

[We](https://abilian.com/) have created Abilian DevTools to help us maintain [our own projects](https://github.com/abilian/), and we thought it could be useful to others.

Here are some of the reasons why we have created this project:

- **Streamlined Tool Collection**: Abilian Devtools brings together a wide range of Python development tools in a single, curated package. This allows developers to focus on their work without spending time searching for and integrating individual tools.

- **Consistency**: By using a curated set of best-of-breed tools, our team can achieve a consistent level of code quality, style, and security across their projects.

- **Simplified Dependency Management**: Instead of managing individual dependencies for each tool, developers only need to add abilian-devtools to their project's `requirements.in` or `pyproject.toml`. This makes it easier to maintain and update dependencies over time.

- **Easy-to-use CLI**: The `adt` command-line utility simplifies common development tasks such as running tests, code formatting, and security audits. This can save time and effort, especially for those new to these tools.

- **Up-to-date Toolset**: Abilian Devtools aims to provide an up-to-date collection of tools, ensuring that developers have access to the latest features and improvements without having to manually track and update each tool.


Roadmap
-------

Here are some ideas for future improvements:

- **Support for additional tools**: for instance, tools that deal with changelogs (via [Conventional Commits](https://www.conventionalcommits.org/)), versioning, documentation...

- **Monorepo support**: Better support for monorepos.

- **Customization**: The curated nature of Abilian Devtools means that it comes with a predefined set of tools. Your project may require additional or alternative tools, or different settings. ADT could help managing (and updating) settings according to your own tastes and needs.

- **Generating configuration and supporting files**: Currently our projects are generated from a template by third-party tools ([Cruft](https://pypi.org/project/cruft/) or [Cookiecutter](https://pypi.org/project/cookiecutter/), using [this template](https://github.com/abilian/cookiecutter-abilian-python)). ADT could help generating configuration files for the various tools (`pyproject.toml`, `setup.cfg`, `noxfile.py`, `Makefile`, `tasks.py`...).

- **Updating configuration and supporting files**: As tools and best practices evolves, and for long-running projects, configuration need to be adapted over time, which can become quite time-consuming, specially when you are working on many small projects (or monorepos). Tools like [Cruft](https://pypi.org/project/cruft/) or [Medikit](https://python-medikit.github.io/)) can help, but in our experience are too fragile. ADT could help with this.

- **CI/CD**: ADT could help with CI/CD integration.

Discussion
----------

- [On GitHub](https://github.com/abilian/abilian-devtools/discussions) (evergreen)
- [On Reddit](https://www.reddit.com/r/Python/comments/136d7yd/abilian_development_tools_a_curated_collection_of/) (May 2023)
- [On AFPY Forum](https://discuss.afpy.org/t/abilian-development-tools-est-une-collection-doutils-de-developpement-python-qui-comprend-des-formateurs-des-frameworks-de-tests-des-verificateurs-de-style-des-verificateurs-de-type-et-des-outils-daudit-de-la-chaine-dapprovisionnement-logicielle/1548) (May 2023, in French)

References
----------

[This presentation from 2017](https://speakerdeck.com/sfermigier/python-quality-engineering-a-tour-of-best-practices) was given at the Paris Open Source Summit (POSS). Many tools have evolved or appeared since then, but the general principles are still valid.

[This presentation from 2005](https://speakerdeck.com/sfermigier/python-best-practices-rmll-2005) was given (in French) at the "Rencontres Mondiales du Logiciel Libre" in Bordeaux. It's obviously outdated, but kept for nostalgic reasons ;)
