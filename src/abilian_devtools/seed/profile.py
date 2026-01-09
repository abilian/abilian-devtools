# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Profile loading and management.

A profile is a directory containing:
- profile.toml: Profile metadata and configuration
- templates/: Files to copy/render
- scripts/: Post-seed scripts
"""

from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

from .config import ADTConfig, load_config


@dataclass
class FileMapping:
    """Mapping from source template to destination file."""

    source: Path
    dest: str
    condition: str | None = None
    is_template: bool = False  # True if source ends with .j2


@dataclass
class ScriptConfig:
    """Configuration for a post-seed script."""

    path: Path
    condition: str | None = None


@dataclass
class Profile:
    """A seed profile configuration."""

    # Profile metadata
    name: str
    description: str = ""
    version: str = "1.0.0"

    # Profile location
    path: Path = field(default_factory=Path)

    # Inheritance
    extends: list[str] = field(default_factory=list)

    # Variables defined by this profile
    variables: dict[str, str | bool | int] = field(default_factory=dict)

    # Variable metadata (descriptions, types, choices)
    variables_meta: dict[str, dict] = field(default_factory=dict)

    # File mappings (source -> dest)
    file_mappings: list[FileMapping] = field(default_factory=list)

    # Scripts to run after seeding
    scripts: list[ScriptConfig] = field(default_factory=list)

    # Script environment variables
    script_env: dict[str, str] = field(default_factory=dict)

    # Conditions for conditional file inclusion
    conditions: dict[str, str] = field(default_factory=dict)

    @property
    def templates_dir(self) -> Path:
        """Path to the templates directory."""
        return self.path / "templates"

    @property
    def scripts_dir(self) -> Path:
        """Path to the scripts directory."""
        return self.path / "scripts"

    def get_template_files(self) -> list[FileMapping]:
        """Get all template files from the templates directory.

        If no explicit file mappings are defined, automatically discovers
        all files in the templates directory.

        Returns:
            List of FileMapping objects for all template files
        """
        if self.file_mappings:
            return self.file_mappings

        # Auto-discover templates
        mappings = []
        templates_dir = self.templates_dir

        if not templates_dir.exists():
            return mappings

        for file_path in templates_dir.rglob("*"):
            if file_path.is_dir():
                continue

            # Skip __pycache__ and other common ignores
            if "__pycache__" in file_path.parts:
                continue

            # Calculate relative path from templates dir
            rel_path = file_path.relative_to(templates_dir)

            # Determine destination name (strip .j2 if present)
            dest_name = str(rel_path)
            is_template = dest_name.endswith(".j2")
            if is_template:
                dest_name = dest_name[:-3]  # Remove .j2

            mappings.append(
                FileMapping(
                    source=file_path,
                    dest=dest_name,
                    is_template=is_template,
                )
            )

        return mappings

    def get_scripts(self) -> list[ScriptConfig]:
        """Get all scripts to run, in order.

        If no explicit scripts are defined, auto-discovers scripts
        in the scripts directory (sorted alphabetically).

        Returns:
            List of ScriptConfig objects
        """
        if self.scripts:
            return self.scripts

        # Auto-discover scripts
        scripts_dir = self.scripts_dir
        if not scripts_dir.exists():
            return []

        script_files = sorted(scripts_dir.glob("*"))
        return [
            ScriptConfig(path=f)
            for f in script_files
            if f.is_file() and not f.name.startswith(".")
        ]


class ProfileError(Exception):
    """Error loading or validating a profile."""


def load_profile(
    name_or_path: str,
    config: ADTConfig | None = None,
) -> Profile:
    """Load a profile by name or path.

    Args:
        name_or_path: Profile name (looked up in config) or path to profile directory
        config: Optional ADT config for looking up profile names

    Returns:
        Loaded Profile instance

    Raises:
        ProfileError: If profile cannot be found or loaded
    """
    # Check if it's a path
    path = Path(name_or_path).expanduser()
    if path.exists() and path.is_dir():
        return _load_profile_from_path(path)

    # Look up by name in config
    if config is None:
        config = load_config()

    profile_path = config.get_profile_path(name_or_path)
    if profile_path is None:
        raise ProfileError(f"Profile not found: {name_or_path}")

    return _load_profile_from_path(profile_path)


def _load_profile_from_path(path: Path) -> Profile:
    """Load a profile from a directory path.

    Args:
        path: Path to profile directory

    Returns:
        Loaded Profile instance

    Raises:
        ProfileError: If profile.toml is missing or invalid
    """
    profile_toml = path / "profile.toml"

    if not profile_toml.exists():
        # Create a minimal profile from directory name
        return Profile(
            name=path.name,
            path=path,
        )

    try:
        content = profile_toml.read_text()
        data = tomlkit.parse(content)
    except Exception as e:
        raise ProfileError(f"Failed to parse {profile_toml}: {e}") from e

    return _parse_profile_data(data, path)


def _parse_profile_data(data: tomlkit.TOMLDocument, path: Path) -> Profile:
    """Parse profile data from TOML document.

    Args:
        data: Parsed TOML document
        path: Path to profile directory

    Returns:
        Profile instance
    """
    profile_section = data.get("profile", {})

    profile = Profile(
        name=str(profile_section.get("name", path.name)),
        description=str(profile_section.get("description", "")),
        version=str(profile_section.get("version", "1.0.0")),
        path=path,
    )

    # Parse extends
    extends = profile_section.get("extends", [])
    if isinstance(extends, str):
        extends = [extends]
    profile.extends = [str(e) for e in extends]

    # Parse variables
    if "variables" in data:
        for key, value in data["variables"].items():
            if key == "meta":
                continue
            profile.variables[key] = value

    # Parse variable metadata
    if "variables" in data and "meta" in data["variables"]:
        for key, meta in data["variables"]["meta"].items():
            profile.variables_meta[key] = dict(meta)

    # Parse file mappings
    if "files" in data:
        profile.file_mappings = _parse_file_mappings(data["files"], path)

    # Parse scripts
    if "scripts" in data:
        scripts_section = data["scripts"]

        # Parse post_seed scripts
        if "post_seed" in scripts_section:
            profile.scripts = _parse_scripts(scripts_section["post_seed"], path)

        # Parse script environment
        if "env" in scripts_section:
            for key, value in scripts_section["env"].items():
                profile.script_env[key] = str(value)

    # Parse conditions
    if "conditions" in data:
        for key, value in data["conditions"].items():
            profile.conditions[key] = str(value)

    return profile


def _parse_file_mappings(files_data: dict, profile_path: Path) -> list[FileMapping]:
    """Parse file mappings from TOML data.

    Args:
        files_data: The [files] section from profile.toml
        profile_path: Path to profile directory

    Returns:
        List of FileMapping objects
    """
    mappings = []
    templates_dir = profile_path / "templates"

    for source, dest_config in files_data.items():
        source_path = templates_dir / source
        if not source_path.exists():
            # Try relative to profile root
            source_path = profile_path / source

        if isinstance(dest_config, str):
            # Simple mapping: "source" = "dest"
            dest = dest_config
            condition = None
        elif isinstance(dest_config, dict):
            # Complex mapping: "source" = { dest = "...", condition = "..." }
            dest = str(dest_config.get("dest", source))
            condition = dest_config.get("condition")
        else:
            continue

        is_template = source.endswith(".j2")
        if is_template and dest.endswith(".j2"):
            dest = dest[:-3]

        mappings.append(
            FileMapping(
                source=source_path,
                dest=dest,
                condition=str(condition) if condition else None,
                is_template=is_template,
            )
        )

    return mappings


def _parse_scripts(scripts_data: list, profile_path: Path) -> list[ScriptConfig]:
    """Parse scripts configuration from TOML data.

    Args:
        scripts_data: List of script paths or configs
        profile_path: Path to profile directory

    Returns:
        List of ScriptConfig objects
    """
    scripts = []

    for item in scripts_data:
        if isinstance(item, str):
            # Simple path
            scripts.append(ScriptConfig(path=profile_path / item))
        elif isinstance(item, dict):
            # Config with condition
            script_path = item.get("script", "")
            condition = item.get("condition")
            scripts.append(
                ScriptConfig(
                    path=profile_path / script_path,
                    condition=str(condition) if condition else None,
                )
            )

    return scripts


def resolve_profile_chain(
    profile_names: list[str],
    config: ADTConfig | None = None,
) -> list[Profile]:
    """Resolve a chain of profiles including inheritance.

    Args:
        profile_names: List of profile names to load (in order)
        config: Optional ADT config

    Returns:
        List of profiles in resolution order (base profiles first)

    Raises:
        ProfileError: If circular dependency detected or profile not found
    """
    if config is None:
        config = load_config()

    resolved: list[Profile] = []
    seen: set[str] = set()

    def resolve_one(name: str) -> None:
        if name in seen:
            return  # Already resolved

        profile = load_profile(name, config)

        # Check for circular dependency
        if name in [p.name for p in resolved if p.name not in seen]:
            raise ProfileError(f"Circular profile dependency detected: {name}")

        seen.add(name)

        # Resolve extended profiles first
        for parent_name in profile.extends:
            resolve_one(parent_name)

        resolved.append(profile)

    for name in profile_names:
        resolve_one(name)

    return resolved


def validate_profile(profile: Profile) -> list[str]:
    """Validate a profile configuration.

    Args:
        profile: Profile to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if not profile.name:
        errors.append("Profile must have a name")

    if not profile.path.exists():
        errors.append(f"Profile path does not exist: {profile.path}")

    # Check templates directory
    templates_dir = profile.templates_dir
    if templates_dir.exists():
        template_files = list(templates_dir.rglob("*"))
        if not any(f.is_file() for f in template_files):
            errors.append(f"Templates directory is empty: {templates_dir}")

    # Validate scripts exist
    for script in profile.scripts:
        if not script.path.exists():
            errors.append(f"Script not found: {script.path}")

    return errors
