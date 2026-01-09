# SPDX-FileCopyrightText: 2023-2026 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Seed command - add configuration files to a project.

Supports profile-based seeding with variable expansion and layered profiles.
"""

import inspect
import os
import stat
import subprocess
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
from ..seed.profile import ProfileError, resolve_profile_chain
from ..seed.variables import parse_cli_vars

IGNORED_FILES = {
    "__pycache__",
    "__init__.py",
    "profile.toml",
}


class SeedCommand(Command):
    """Seed project with configuration files from profiles."""

    name = "seed"

    arguments = []

    options = [
        Option("-p", "--profile", metavar="NAME", help="Profile name or path"),
        Option("-l", "--list", action="store_true", help="List profiles"),
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
        list: bool = False,  # noqa: A002
        info: str | None = None,
        overwrite: bool = False,
        yes: bool = False,
        dry_run: bool = False,
        var: list[str] | None = None,
    ):
        config = load_config()

        # Handle --list
        if list:
            self._list_profiles(config)
            return

        # Handle --info
        if info:
            self._show_profile_info(info, config)
            return

        self._run_seed(
            profile=profile,
            var=var or [],
            overwrite=overwrite,
            yes=yes,
            dry_run=dry_run,
            config=config,
        )

    def _run_seed(
        self,
        profile: str | None = None,
        var: list[str] | None = None,
        *,
        overwrite: bool = False,
        yes: bool = False,
        dry_run: bool = False,
        config: ADTConfig | None = None,
    ):
        config = config or load_config()

        print(bold("Seeding project..."))

        # Determine which profile to use
        profiles = self._resolve_profile(profile, config)

        if not profiles:
            # Fallback to built-in templates
            print(dim("No profile specified, using built-in templates"))
            self._seed_builtin(overwrite=overwrite, yes=yes, dry_run=dry_run)
            return

        # Parse CLI variables
        cli_vars = parse_cli_vars(var or [])

        # Create variable resolver
        resolver = VariableResolver(
            cli_vars=cli_vars,
            profiles=profiles,
            config=config,
            project_dir=Path.cwd(),
        )

        # Resolve variables
        context = resolver.resolve()

        # Seed each profile in order
        for p in profiles:
            self._seed_profile(p, context, overwrite=overwrite, yes=yes, dry_run=dry_run)

        # Run scripts from all profiles
        if not dry_run:
            self._run_all_scripts(profiles, context, config, yes=yes)

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
            List of Profile objects (handles inheritance)
        """
        # Use default profile if none specified
        profile_spec = profile_arg or config.default_profile
        if not profile_spec:
            return []

        # Get profile path (handles both names and paths)
        profile_path = config.get_profile_path(profile_spec)
        if not profile_path:
            print(f"Error: Profile not found: {profile_spec}")
            if config.profiles_dir:
                print(f"  Looked in: {config.profiles_dir}")
            else:
                print("  Hint: Set profiles_dir in config or use full path")
            return []

        # Load profile and resolve inheritance chain
        # Pass the actual path string to handle direct paths correctly
        try:
            return resolve_profile_chain([str(profile_path)], config)
        except ProfileError as e:
            print(f"Error: {e}")
            return []

    def _seed_profile(
        self,
        profile: Profile,
        context: dict,
        *,
        overwrite: bool,
        yes: bool,
        dry_run: bool,
    ):
        """Seed files from a single profile.

        Args:
            profile: Profile to seed from
            context: Variable context for template rendering
            overwrite: Whether to overwrite existing files
            yes: Skip confirmation prompts
            dry_run: Don't actually write files
        """
        print(f"\nProfile: {bold(profile.name)}")

        template_files = profile.get_template_files()

        if not template_files:
            print(dim("  No template files found"))
            return

        project_dir = Path.cwd()

        for mapping in template_files:
            # Evaluate condition if present
            if mapping.condition and not evaluate_condition(
                mapping.condition, context, project_dir
            ):
                msg = f"  {dim('skip')} {mapping.dest} (condition: {mapping.condition})"
                print(msg)
                continue

            dest_path = Path(mapping.dest)

            # Check if file exists
            if dest_path.exists():
                if not overwrite:
                    print(f"  {dim('skip')} {mapping.dest} (exists)")
                    continue
                if not yes and not dry_run:
                    response = input(f"  Overwrite {mapping.dest}? [y/N] ")
                    if response.lower() != "y":
                        print(f"  {dim('skip')} {mapping.dest}")
                        continue

            # Read source content
            if not mapping.source.exists():
                print(f"  {dim('error')} {mapping.dest} (source not found)")
                continue

            content = mapping.source.read_text()

            # Render template if needed
            if mapping.is_template:
                try:
                    content = render_template(content, context, project_dir)
                except Exception as e:
                    print(f"  {dim('error')} {mapping.dest} (template error: {e})")
                    continue

            # Write file
            action = "overwrite" if dest_path.exists() else "create"
            if dry_run:
                print(f"  {dim(f'would {action}')} {mapping.dest}")
            else:
                # Ensure parent directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(content)
                print(f"  {action} {mapping.dest}")

    def _run_all_scripts(
        self,
        profiles: list[Profile],
        context: dict,
        config: ADTConfig,
        *,
        yes: bool,
    ):
        """Run scripts from all profiles.

        Args:
            profiles: List of profiles (in resolution order)
            context: Variable context
            config: ADT config
            yes: Skip confirmation prompts
        """
        # Collect all scripts from all profiles
        all_scripts = []
        for profile in profiles:
            scripts = profile.get_scripts()
            if scripts:
                all_scripts.append((profile, scripts))

        if not all_scripts:
            return

        print(bold("\nRunning post-seed scripts..."))

        # Check if confirmation is required
        if config.confirm_scripts and not yes:
            print()
            print(yellow("The following scripts will be executed:"))
            for profile, scripts in all_scripts:
                for script in scripts:
                    print(f"  {dim(profile.name + '/')} {script.path.name}")
            print()
            response = input("Run these scripts? [y/N] ")
            if response.lower() != "y":
                print(dim("Scripts skipped"))
                return

        # Run scripts
        project_dir = Path.cwd()
        for profile, scripts in all_scripts:
            self._run_profile_scripts(profile, scripts, context, project_dir)

    def _run_profile_scripts(
        self,
        profile: Profile,
        scripts: list,
        context: dict,
        project_dir: Path,
    ):
        """Run scripts from a single profile.

        Args:
            profile: The profile
            scripts: List of ScriptConfig objects
            context: Variable context
            project_dir: Project directory (cwd)
        """
        for script in scripts:
            # Evaluate condition if present
            if script.condition and not evaluate_condition(
                script.condition, context, project_dir
            ):
                print(f"  {dim('skip')} {script.path.name} (condition: {script.condition})")
                continue

            # Check script exists
            if not script.path.exists():
                print(f"  {red('error')} {script.path.name} (not found)")
                continue

            # Build environment
            env = self._build_script_env(profile, context)

            # Run the script
            self._execute_script(script.path, env, project_dir)

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
        for key, value in profile.script_env.items():
            env[key] = value

        # Add some useful defaults
        env["ADT_PROFILE"] = profile.name
        env["ADT_PROFILE_PATH"] = str(profile.path)

        return env

    def _execute_script(self, script_path: Path, env: dict, cwd: Path):
        """Execute a single script.

        Args:
            script_path: Path to the script
            env: Environment variables
            cwd: Working directory
        """
        script_name = script_path.name

        # Make script executable if it isn't
        if not os.access(script_path, os.X_OK):
            current_mode = script_path.stat().st_mode
            script_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        print(f"  {dim('run')} {script_name}")

        try:
            result = subprocess.run(
                [str(script_path)],
                cwd=cwd,
                env=env,
                capture_output=False,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                print(f"  {green('ok')} {script_name}")
            else:
                print(f"  {red('failed')} {script_name} (exit code: {result.returncode})")

        except Exception as e:
            print(f"  {red('error')} {script_name}: {e}")

    def _seed_builtin(self, *, overwrite: bool, yes: bool, dry_run: bool):
        """Seed from built-in templates (backward compatibility).

        Args:
            overwrite: Whether to overwrite existing files
            yes: Skip confirmation prompts
            dry_run: Don't actually write files
        """
        etc_root = get_package_root("abilian_devtools") / "etc"

        for file in etc_root.iterdir():
            # Skip directories
            if file.is_dir():
                continue

            name = file.name
            if name in IGNORED_FILES:
                continue

            self._add_builtin_file(file, overwrite=overwrite, yes=yes, dry_run=dry_run)

    def _add_builtin_file(
        self,
        file: Path,
        *,
        overwrite: bool,
        yes: bool,
        dry_run: bool,
    ):
        """Add a single built-in file.

        Args:
            file: Source file path
            overwrite: Whether to overwrite existing files
            yes: Skip confirmation prompts
            dry_run: Don't actually write files
        """
        name = file.name
        metadata = self._get_metadata(file)
        name = metadata.get("name", name)
        dest_path = Path(name)

        if dest_path.exists():
            if not overwrite:
                print(f"  {dim('skip')} {name} (exists)")
                return
            if not yes and not dry_run:
                response = input(f"  Overwrite {name}? [y/N] ")
                if response.lower() != "y":
                    print(f"  {dim('skip')} {name}")
                    return

        content = file.read_text()

        action = "overwrite" if dest_path.exists() else "create"
        if dry_run:
            print(f"  {dim(f'would {action}')} {name}")
        else:
            dest_path.write_text(content)
            print(f"  {action} {name}")

    def _get_metadata(self, file: Path) -> dict:
        """Extract ADT metadata from file comments.

        Args:
            file: File to extract metadata from

        Returns:
            Dictionary of metadata key-value pairs
        """
        metadata = {}
        content = file.read_text()
        lines = content.splitlines()
        for line in lines:
            if "ADT:" not in line:
                continue
            key, value = line.split("ADT:")[1].split("=", 1)
            metadata[key.strip()] = value.strip()
        return metadata

    def _list_profiles(self, config: ADTConfig):
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
            print("To add profiles, either:")
            print("  1. Create profiles in ~/.config/adt/profiles/")
            print("  2. Add sources to ~/.config/adt/config.toml")
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

    def _show_profile_info(self, name: str, config: ADTConfig):
        """Show detailed information about a profile.

        Args:
            name: Profile name
            config: Global ADT config
        """
        try:
            profile = load_profile(name, config)
        except ProfileError as e:
            print(f"Error: {e}")
            return

        print(bold(f"Profile: {profile.name}"))
        print()

        if profile.description:
            print(f"Description: {profile.description}")

        print(f"Version: {profile.version}")
        print(f"Path: {profile.path}")

        if profile.extends:
            print(f"Extends: {', '.join(profile.extends)}")

        # Variables
        if profile.variables:
            print()
            print(bold("Variables:"))
            for key, value in profile.variables.items():
                print(f"  {key} = {value}")

        # Template files
        template_files = profile.get_template_files()
        if template_files:
            print()
            print(bold("Template files:"))
            for mapping in template_files:
                suffix = " (jinja2)" if mapping.is_template else ""
                print(f"  {mapping.dest}{dim(suffix)}")

        # Scripts
        scripts = profile.get_scripts()
        if scripts:
            print()
            print(bold("Scripts:"))
            for script in scripts:
                print(f"  {script.path.name}")


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
