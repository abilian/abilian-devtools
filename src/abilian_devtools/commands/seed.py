# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Seed command - add configuration files to a project.

Supports profile-based seeding with variable expansion and layered profiles.
"""

import inspect
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

from cleez.colors import bold, dim, green, red, yellow
from cleez.command import Command, Option

from ..seed import (
    ADTConfig,
    Profile,
    VariableResolver,
    evaluate_condition,
    load_config,
    load_profile,
    render_template,
)
from ..seed.config import ConfigError
from ..seed.profile import FileMapping, ProfileError, resolve_profile_chain
from ..seed.template import ConditionError
from ..seed.variables import parse_cli_vars

IGNORED_FILES = {
    "__pycache__",
    "__init__.py",
    "profile.toml",
}

# In a built-in file, a comment such as `# ADT: name=.gitignore`.
METADATA_RE = re.compile(r"ADT:\s*(\w+)\s*=\s*(\S+)")


class UserCancelledError(Exception):
    """Raised when user cancels with Ctrl+C."""


class SeedFailedError(Exception):
    """Seeding ran, but some files or scripts failed."""


def prompt(message: str) -> str:
    """Prompt user for input, handling Ctrl+C gracefully.

    Args:
        message: The prompt message to display

    Returns:
        User's input string

    Raises:
        UserCancelledError: If user presses Ctrl+C
    """
    try:
        return input(message)
    except KeyboardInterrupt:
        print()  # New line after ^C
        raise UserCancelledError from None


def error(message: str) -> None:
    """Print an error on stderr."""
    print(red(message), file=sys.stderr)


class SeedCommand(Command):
    """Seed project with configuration files from profiles."""

    name = "seed"

    arguments = []

    options = [
        Option("-p", "--profile", metavar="NAME", help="Profile name or path"),
        Option(
            "-l",
            "--list",
            dest="list_profiles",
            action="store_true",
            help="List profiles",
        ),
        Option("-i", "--info", metavar="PROFILE", help="Show profile info"),
        Option("-o", "--overwrite", action="store_true", help="Overwrite files"),
        Option("-y", "--yes", action="store_true", help="Skip confirmations"),
        Option("-n", "--dry-run", action="store_true", help="Dry run mode"),
        Option("-v", "--var", action="append", metavar="K=V", help="Set variable"),
    ]

    def run(
        self,
        profile: str | None = None,
        *,
        list_profiles: bool = False,
        info: str | None = None,
        overwrite: bool = False,
        yes: bool = False,
        dry_run: bool = False,
        var: list[str] | None = None,
    ) -> None:
        try:
            cli_vars = parse_cli_vars(var or [])
        except ValueError as e:
            error(f"seed can't run: {e}")
            raise SystemExit(1) from None

        try:
            config = load_config()
            if list_profiles:
                self._list_profiles(config)
            elif info:
                self._show_profile_info(info, config)
            else:
                self._run_seed(
                    profile=profile,
                    cli_vars=cli_vars,
                    overwrite=overwrite,
                    yes=yes,
                    dry_run=dry_run,
                    config=config,
                )
        except UserCancelledError:
            print(dim("Cancelled"))
        except (ConfigError, ProfileError) as e:
            error(f"seed can't run: {e}")
            raise SystemExit(1) from None
        except SeedFailedError as e:
            error(f"seed failed: {e}")
            raise SystemExit(1) from None

    def _run_seed(
        self,
        profile: str | None,
        cli_vars: dict,
        *,
        overwrite: bool,
        yes: bool,
        dry_run: bool,
        config: ADTConfig,
    ) -> None:
        print(bold("Seeding project..."))

        profiles = self._resolve_profile(profile, config)

        if not profiles:
            print(dim("No profile specified, using built-in templates"))
            failures = self._seed_profile(
                builtin_profile(),
                {},
                overwrite=overwrite,
                yes=yes,
                dry_run=dry_run,
            )
            self._report(failures, dry_run=dry_run)
            return

        resolver = VariableResolver(
            cli_vars=cli_vars,
            profiles=profiles,
            config=config,
            project_dir=Path.cwd(),
        )
        context = resolver.resolve()

        failures = 0
        for p in profiles:
            failures += self._seed_profile(
                p, context, overwrite=overwrite, yes=yes, dry_run=dry_run
            )

        if not dry_run:
            failures += self._run_all_scripts(profiles, context, config, yes=yes)

        self._report(failures, dry_run=dry_run)

    def _report(self, failures: int, *, dry_run: bool) -> None:
        if failures:
            msg = f"{failures} file(s) or script(s) failed, see above"
            raise SeedFailedError(msg)
        if dry_run:
            print(dim("\nDry run - no files were modified"))
        else:
            print(bold("\nSeeding complete!"))

    def _resolve_profile(
        self,
        profile_arg: str | None,
        config: ADTConfig,
    ) -> list[Profile]:
        """Resolve profile from argument or config.

        Args:
            profile_arg: Profile name or path from CLI (-p option)
            config: ADT config

        Returns:
            List of Profile objects (handles inheritance), empty if no profile
            was named, on the command line or in the config

        Raises:
            ProfileError: If the profile named can't be found or loaded
        """
        profile_spec = profile_arg or config.default_profile
        if not profile_spec:
            return []

        profile_path = config.get_profile_path(profile_spec)
        if not profile_path:
            if config.profiles_dir:
                hint = f"looked in {config.profiles_dir}"
            else:
                hint = (
                    "no profiles_dir is configured: set one in "
                    "~/.config/adt/config.toml, or give the profile's path"
                )
            msg = f"profile {profile_spec!r} not found ({hint})"
            raise ProfileError(msg)

        # Pass the actual path string to handle direct paths correctly
        return resolve_profile_chain([str(profile_path)], config)

    def _seed_profile(
        self,
        profile: Profile,
        context: dict,
        *,
        overwrite: bool,
        yes: bool,
        dry_run: bool,
    ) -> int:
        """Seed files from a single profile.

        Args:
            profile: Profile to seed from
            context: Variable context for template rendering
            overwrite: Whether to overwrite existing files
            yes: Skip confirmation prompts
            dry_run: Don't actually write files

        Returns:
            The number of files that failed
        """
        print(f"\nProfile: {bold(profile.name)}")

        template_files = profile.get_template_files()

        if not template_files:
            print(dim("  No template files found"))
            return 0

        project_dir = Path.cwd()
        accept_all = yes  # Track if user selected "all"
        failures = 0

        for mapping in template_files:
            try:
                if mapping.condition and not evaluate_condition(
                    mapping.condition, context, project_dir
                ):
                    print(
                        f"  {dim('skip')} {mapping.dest} "
                        f"(condition: {mapping.condition})"
                    )
                    continue
            except ConditionError as e:
                error(f"  {mapping.dest}: {e}")
                failures += 1
                continue

            dest_path = Path(mapping.dest)
            file_exists = dest_path.exists()

            if file_exists and not overwrite:
                print(f"  {dim('skip')} {mapping.dest} (exists)")
                continue

            action = "overwrite" if file_exists else "create"
            if not accept_all and not dry_run:
                response = prompt(
                    f"  {action.capitalize()} {mapping.dest}? [y/N/a] "
                ).lower()
                if response == "a":
                    accept_all = True
                elif response != "y":
                    print(f"  {dim('skip')} {mapping.dest}")
                    continue

            if not mapping.source.exists():
                error(f"  {mapping.dest}: source {mapping.source} not found")
                failures += 1
                continue

            content = mapping.source.read_text()

            if mapping.is_template:
                try:
                    content = render_template(content, context, project_dir)
                except Exception as e:
                    error(f"  {mapping.dest}: template error: {e}")
                    failures += 1
                    continue

            if dry_run:
                print(f"  {dim(f'would {action}')} {mapping.dest}")
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(content)
                print(f"  {action} {mapping.dest}")

        return failures

    def _run_all_scripts(
        self,
        profiles: list[Profile],
        context: dict,
        config: ADTConfig,
        *,
        yes: bool,
    ) -> int:
        """Run scripts from all profiles.

        Args:
            profiles: List of profiles (in resolution order)
            context: Variable context
            config: ADT config
            yes: Skip confirmation prompts

        Returns:
            The number of scripts that failed
        """
        all_scripts = [(p, p.get_scripts()) for p in profiles if p.get_scripts()]
        if not all_scripts:
            return 0

        print(bold("\nRunning post-seed scripts..."))

        if config.confirm_scripts and not yes:
            print()
            print(yellow("The following scripts will be executed:"))
            for profile, scripts in all_scripts:
                for script in scripts:
                    print(f"  {dim(profile.name + '/')} {script.path.name}")
            print()
            response = prompt("Run these scripts? [y/N] ")
            if response.lower() != "y":
                print(dim("Scripts skipped"))
                return 0

        project_dir = Path.cwd()
        failures = 0
        for profile, scripts in all_scripts:
            failures += self._run_profile_scripts(
                profile, scripts, context, project_dir
            )
        return failures

    def _run_profile_scripts(
        self,
        profile: Profile,
        scripts: list,
        context: dict,
        project_dir: Path,
    ) -> int:
        """Run scripts from a single profile.

        Args:
            profile: The profile
            scripts: List of ScriptConfig objects
            context: Variable context
            project_dir: Project directory (cwd)

        Returns:
            The number of scripts that failed
        """
        failures = 0
        for script in scripts:
            try:
                if script.condition and not evaluate_condition(
                    script.condition, context, project_dir
                ):
                    print(
                        f"  {dim('skip')} {script.path.name} "
                        f"(condition: {script.condition})"
                    )
                    continue
            except ConditionError as e:
                error(f"  {script.path.name}: {e}")
                failures += 1
                continue

            if not script.path.exists():
                error(f"  {script.path.name}: script {script.path} not found")
                failures += 1
                continue

            env = self._build_script_env(profile, context)
            if not self._execute_script(script.path, env, project_dir):
                failures += 1
        return failures

    def _build_script_env(self, profile: Profile, context: dict) -> dict:
        """Build environment variables for script execution.

        Args:
            profile: The profile (for script_env)
            context: Variable context

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()

        # Add context variables (convert to strings)
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                env[f"ADT_{key.upper()}"] = str(value)

        # Add profile-specific script environment
        env.update(profile.script_env)

        env["ADT_PROFILE"] = profile.name
        env["ADT_PROFILE_PATH"] = str(profile.path)

        return env

    def _execute_script(self, script_path: Path, env: dict, cwd: Path) -> bool:
        """Execute a single script.

        Args:
            script_path: Path to the script
            env: Environment variables
            cwd: Working directory

        Returns:
            True if the script ran and exited with status 0
        """
        script_name = script_path.name

        # Make script executable if it isn't
        if not os.access(script_path, os.X_OK):
            current_mode = script_path.stat().st_mode
            script_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        print(f"  {dim('run')} {script_name}")

        try:
            result = subprocess.run([str(script_path)], cwd=cwd, env=env, check=False)
        except OSError as e:
            error(f"  {script_name} can't be run: {e}")
            return False

        if result.returncode != 0:
            error(f"  {script_name} failed with exit status {result.returncode}")
            return False

        print(f"  {green('ok')} {script_name}")
        return True

    def _list_profiles(self, config: ADTConfig) -> None:
        """List available profiles.

        Args:
            config: Global ADT config
        """
        print(bold("Available profiles:"))
        print()

        profiles = config.list_profiles()

        if not profiles:
            print(dim("  No profiles configured"))
            print()
            print("To add profiles, set profiles_dir to a directory of profiles,")
            print("in the [seed] section of ~/.config/adt/config.toml")
            print("or of the project's .adt-config.toml.")
            return

        for name in profiles:
            try:
                profile = load_profile(name, config)
                desc = profile.description or dim("No description")
                print(f"  {bold(name)}: {desc}")
            except ProfileError:
                print(f"  {bold(name)}: {dim('(error loading)')}")

        if config.default_profile:
            print()
            print(f"Default profile: {bold(config.default_profile)}")

    def _show_profile_info(self, name: str, config: ADTConfig) -> None:
        """Show detailed information about a profile.

        Args:
            name: Profile name
            config: Global ADT config

        Raises:
            ProfileError: If the profile can't be found or loaded
        """
        profile = load_profile(name, config)

        print(bold(f"Profile: {profile.name}"))
        print()

        if profile.description:
            print(f"Description: {profile.description}")

        print(f"Version: {profile.version}")
        print(f"Path: {profile.path}")

        if profile.extends:
            print(f"Extends: {', '.join(profile.extends)}")

        if profile.variables:
            print()
            print(bold("Variables:"))
            for key, value in profile.variables.items():
                print(f"  {key} = {value}")

        template_files = profile.get_template_files()
        if template_files:
            print()
            print(bold("Template files:"))
            for mapping in template_files:
                suffix = " (jinja2)" if mapping.is_template else ""
                print(f"  {mapping.dest}{dim(suffix)}")

        scripts = profile.get_scripts()
        if scripts:
            print()
            print(bold("Scripts:"))
            for script in scripts:
                print(f"  {script.path.name}")


def builtin_profile() -> Profile:
    """The files shipped in the package's `etc` directory, as a profile.

    A file is seeded under the name its `ADT: name=...` comment gives, or its
    own (a dotfile can't always be shipped under its name).
    """
    etc_root = get_package_root("abilian_devtools") / "etc"
    mappings = [
        FileMapping(source=file, dest=get_metadata(file).get("name", file.name))
        for file in sorted(etc_root.iterdir())
        if file.is_file() and file.name not in IGNORED_FILES
    ]
    return Profile(name="built-in", path=etc_root, file_mappings=mappings)


def get_metadata(file: Path) -> dict[str, str]:
    """The `ADT: key=value` metadata in a file's comments."""
    return dict(METADATA_RE.findall(file.read_text()))


def get_package_root(package_name: str) -> Path:
    """Get the root directory of an installed package.

    Args:
        package_name: Name of the package

    Returns:
        Path to the package root directory
    """
    module = __import__(package_name)
    package_path = inspect.getfile(module)
    return Path(package_path).parent
