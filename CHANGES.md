# Changes

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2025-01-09

### Added
- **Seed command overhaul**: Complete rewrite of the `adt seed` command with profile-based project scaffolding
  - Profile-based templates with inheritance (`extends` support)
  - Jinja2 template rendering with custom filters and functions
  - Variable resolution from multiple sources (pyproject.toml, config, profiles, env, CLI)
  - Post-seed script execution with confirmation prompts
  - Hierarchical configuration: `~/.config/adt/config.toml` (global) → `.adt-config.toml` (project) → `-c` (CLI)
  - New CLI options: `-p/--profile`, `-l/--list`, `-i/--info`, `-o/--overwrite`, `-y/--yes`, `-n/--dry-run`, `-v/--var`
- New template filters: `snake_case`, `kebab_case`, `camel_case`, `pascal_case`, `slug`, `pluralize`
- New template functions: `now()`, `env()`, `exists()`, `read_file()`
- Condition evaluation for conditional file inclusion and script execution
- New `typecheck` command using `ty` type checker (`adt typecheck src`)

### Changed
- Configuration simplified: replaced `sources` dict with single `profiles_dir` path
- Boolean function arguments now keyword-only (fixes ruff FBT001)
- **BREAKING**: Replaced type checkers `mypy`, `pyright`, `pyrefly` with `ty`
- **BREAKING**: Removed `black` and `isort` (ruff handles formatting and import sorting)
- Modernized all Poetry references to uv
- Updated `bump-version` command to only support modern pyproject.toml format
- Updated `cruft` command to check for `uv.lock` instead of `poetry.lock`
- Migrated `tool.uv.dev-dependencies` to `dependency-groups.dev`
- Updated Makefile templates with uv commands

### Removed
- Removed `setup.cfg` (flake8/mypy configs no longer needed)
- Removed `tox.ini` (project uses nox)
- Removed Poetry version fallback in version management

### Fixed
- Fixed type errors found by `ty` type checker
- Fixed typo in cruft command (`tox.init` → `tox.ini`)

## [0.8.0] - 2025-10-06

### Changed
- Updated dependencies to latest versions and removed flake8 and plugins.

## [0.7.7] - 2025-04-22

### Changed
- Updated dependencies and configuration

## [0.7.6] - 2024-12-17

### Removed
- Removed `git-cliff` from dependencies

### Changed
- Updated dependencies

## [0.7.5] - 2024-11-28

### Removed
- Removed `pip-audit` from audit command due to reliability issues

### Fixed
- Fixed Makefile targets

## [0.7.4] - 2024-11-19

### Changed
- Relaxed version constraints on dependencies for better compatibility

## [0.7.3] - 2024-11-04

### Changed
- Updated dependencies

## [0.7.2] - 2024-11-04

### Changed
- Updated dependencies

## [0.7.1] - 2024-11-04

### Changed
- Updated dependencies

## [0.7.0] - 2024-10-29

### Changed
- **BREAKING**: Migrated project from Poetry to uv for dependency management and building
- Updated all tooling to work with uv

## [0.6.8] - 2024-10-29

### Added
- Support for both Poetry and uv version schemes in `bump-version` command

## [0.6.7] - 2024-10-25

### Changed
- Improved handling of default targets (`src` and `tests`) in commands
- Commands now correctly default to these directories when no arguments provided

## [0.6.6] - 2024-10-10

### Changed
- Made argument validation more resilient in check command

## [0.6.5] - 2024-10-07

### Changed
- Updated dependencies

## [0.6.4] - 2024-09-02

### Changed
- Updated dependencies

## [0.6.3] - 2024-08-29

### Changed
- Updated dependencies and configuration

## [0.6.2] - 2024-08-02

### Changed
- Updated `deptry` to latest version

## [0.6.1] - 2024-07-31

### Added
- New `seed` command to generate common configuration files
- Support for multiple seed file templates

## [0.5.27] - 2024-07-15

### Added
- Added `git-cliff` for automated changelog generation

## [0.5.26] - 2024-07-15

### Added
- Added `dlint` security linter to dependencies

## [0.5.24] - 2024-07-04

### Documentation
- Improved changelog generation configuration

## [0.5.16] - 2024-02-01

### Changed
- Relaxed version constraints on `pytest` dependency

## [0.5.13] - 2023-11-07

### Changed
- Extended cruft detection to check for additional files

## [0.5.12] - 2023-11-07

### Added
- New `cruft` command for detecting and cleaning cruft files

### Documentation
- Updated project documentation

## [0.5.11] - 2023-10-04

### Documentation
- Added git-cliff configuration
- Updated changelog format

## [0.5.8] - 2023-09-08

### Changed
- Improved help message formatting and clarity

## [0.5.6] - 2023-09-06

### Documentation
- Improved README with better explanations and examples
- Added links to presentation slides

## [0.5.2] - 2023-05-03

### Added
- Support for multiple ruff configuration file locations (e.g., `etc/ruff.toml`)

### Documentation
- Added comprehensive explanations in README

### Fixed
- Fixed noxfile configuration

## [0.5.1] - 2023-04-25

### Fixed
- Updated cleez dependency to fix duplicate command issue

## [0.4.19] - 2023-04-25

### Changed
- **BREAKING**: Migrated from custom CLI framework to cleez
- Refactored and deduplicated command implementations

## [0.4.18] - 2023-04-10

### Added
- New `format` command to format code with black and isort

## [0.4.17] - 2023-04-10

### Fixed
- Fixed `help-make` command not being properly imported

## [0.4.15] - 2023-03-30

### Fixed
- Commands now properly exit with non-zero status on failure

### Documentation
- Updated README

## [0.4.14] - 2023-03-29

### Fixed
- Fixed `bump-version` to tag the correct commit

## [0.4.13] - 2023-03-29

### Changed
- Added more explicit status messages during command execution

## [0.4.12] - 2023-03-28

### Added
- New `help-make` command to generate help text for Makefiles

## [0.4.11] - 2023-03-03

### Changed
- Enhanced `clean` command to remove additional cruft

## [0.4.10] - 2023-02-16

### Added
- New `bump-version` command for automated version bumping, committing, and tagging
- Support for selective Invoke task imports

### Fixed
- Fixed Makefile parsing issues

## [0.4.5] - 2023-02-13

### Added
- Experimental support for Invoke tasks

## [0.4.4] - 2023-02-01

### Added
- Initial CLI implementation with `adt` command
- `check` command for running linters (ruff, vulture, deptry)
- `clean` command for cleaning build artifacts
- `audit` command for security auditing
- `test` command for running pytest

### Documentation
- Created initial README
- Added changelog

### Testing
- Added basic CLI tests

## Earlier Versions

Earlier versions were internal releases without public documentation.
