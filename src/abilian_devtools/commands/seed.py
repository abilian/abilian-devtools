# SPDX-FileCopyrightText: 2023 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Seed command - add configuration files to a project.

Supports profile-based seeding with variable expansion and layered profiles.
"""

import inspect
import re
from pathlib import Path

from cleez.colors import bold, dim
from cleez.command import Argument, Command
from jinja2 import Environment

from ..seed import (
    ADTConfig,
    Profile,
    VariableResolver,
    load_config,
    load_profile,
)
from ..seed.profile import ProfileError, resolve_profile_chain
from ..seed.variables import parse_cli_vars

IGNORED_FILES = {
    "__pycache__",
    "__init__.py",
    "profile.toml",
}


class SeedCommand(Command):
    """Seed project (add useful config files).

    Usage:
      adt seed                     Use default profile or built-in templates
      adt seed PROFILE             Use specified profile (comma-separated for layering)
      adt seed list                List available profiles
      adt seed info PROFILE        Show profile information

    Special arguments:
      overwrite                    Overwrite existing files (with confirmation)
      force                        Overwrite without confirmation
      dry                          Show what would be done (dry run)
    """

    name = "seed"

    arguments = [
        Argument("args", nargs="*", help="Profile name or action (list, info)"),
    ]

    def run(self, args: list[str] | None = None):
        args = args or []

        # Handle special actions
        if args and args[0] == "list":
            config = load_config()
            self._list_profiles(config)
            return

        if args and args[0] == "info":
            if len(args) < 2:
                print("Usage: adt seed info PROFILE")
                return
            config = load_config()
            self._show_profile_info(args[1], config)
            return

        # Parse remaining arguments
        profile: str | None = None
        overwrite = False
        yes = False
        dry_run = False

        for arg in args:
            if arg == "overwrite":
                overwrite = True
            elif arg == "force":
                overwrite = True
                yes = True
            elif arg == "dry":
                dry_run = True
            elif not profile:
                profile = arg

        self._run_seed(
            profile=profile,
            source=None,
            var=[],
            overwrite=overwrite,
            yes=yes,
            dry_run=dry_run,
            list_profiles=False,
            info=None,
        )

    def _run_seed(
        self,
        profile: str | None = None,
        source: str | None = None,
        var: list[str] | None = None,
        overwrite: bool = False,
        yes: bool = False,
        dry_run: bool = False,
        list_profiles: bool = False,
        info: str | None = None,
    ):
        # Load global config
        config = load_config()

        # Handle --list
        if list_profiles:
            self._list_profiles(config)
            return

        # Handle --info
        if info:
            self._show_profile_info(info, config)
            return

        print(bold("Seeding project..."))

        # Determine which profiles/source to use
        profiles = self._resolve_profiles(profile, source, config)

        if not profiles:
            # Fallback to built-in templates
            print(dim("No profiles configured, using built-in templates"))
            self._seed_builtin(overwrite, yes, dry_run)
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
            self._seed_profile(p, context, overwrite, yes, dry_run)

        if dry_run:
            print(dim("\nDry run - no files were modified"))
        else:
            print(bold("\nSeeding complete!"))

    def _resolve_profiles(
        self,
        profile_arg: str | None,
        source: str | None,
        config: ADTConfig,
    ) -> list[Profile]:
        """Resolve profiles from arguments or config.

        Args:
            profile_arg: Comma-separated profile names from CLI
            source: One-off source directory
            config: Global ADT config

        Returns:
            List of Profile objects in resolution order
        """
        # One-off source takes precedence
        if source:
            source_path = Path(source).expanduser()
            if not source_path.exists():
                print(f"Error: Source directory not found: {source}")
                return []
            try:
                return [load_profile(str(source_path), config)]
            except ProfileError as e:
                print(f"Error loading source: {e}")
                return []

        # Parse profile argument
        if profile_arg:
            profile_names = [p.strip() for p in profile_arg.split(",")]
        elif config.default_profile:
            profile_names = [config.default_profile]
        else:
            return []

        # Resolve profile chain (handles inheritance)
        try:
            return resolve_profile_chain(profile_names, config)
        except ProfileError as e:
            print(f"Error: {e}")
            return []

    def _seed_profile(
        self,
        profile: Profile,
        context: dict,
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

        for mapping in template_files:
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
                content = self._render_template(content, context)

            # Write file
            action = "overwrite" if dest_path.exists() else "create"
            if dry_run:
                print(f"  {dim(f'would {action}')} {mapping.dest}")
            else:
                # Ensure parent directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(content)
                print(f"  {action} {mapping.dest}")

    def _render_template(self, content: str, context: dict) -> str:
        """Render a Jinja2 template.

        Args:
            content: Template content
            context: Variable context

        Returns:
            Rendered content
        """
        try:
            env = Environment(
                keep_trailing_newline=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )

            # Add custom filters
            env.filters["snake_case"] = self._snake_case
            env.filters["kebab_case"] = self._kebab_case
            env.filters["pascal_case"] = self._pascal_case

            template = env.from_string(content)
            return template.render(**context)
        except ImportError:
            print("Warning: jinja2 not installed, skipping template rendering")
            return content
        except Exception as e:
            print(f"Warning: Template rendering failed: {e}")
            return content

    @staticmethod
    def _snake_case(value: str) -> str:
        """Convert string to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", value)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
        return s2.replace("-", "_").lower()

    @staticmethod
    def _kebab_case(value: str) -> str:
        """Convert string to kebab-case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1-\2", value)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1-\2", s1)
        return s2.replace("_", "-").lower()

    @staticmethod
    def _pascal_case(value: str) -> str:
        """Convert string to PascalCase."""
        parts = value.replace("-", "_").split("_")
        return "".join(word.capitalize() for word in parts)

    def _seed_builtin(self, overwrite: bool, yes: bool, dry_run: bool):
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

            self._add_builtin_file(file, overwrite, yes, dry_run)

    def _add_builtin_file(
        self,
        file: Path,
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
            print(f"  1. Create profiles in ~/.config/adt/profiles/")
            print(f"  2. Add sources to ~/.config/adt/config.toml")
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
