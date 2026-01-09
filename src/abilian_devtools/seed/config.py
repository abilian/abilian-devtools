# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Global ADT configuration management.

Configuration is loaded hierarchically:
1. ~/.config/adt/config.toml (global defaults)
2. .adt-config.toml (project-specific overrides)
3. Command-line options (highest priority)
"""

from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

# Default config locations
GLOBAL_CONFIG_DIR = Path.home() / ".config" / "adt"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.toml"
PROJECT_CONFIG_FILE = ".adt-config.toml"


@dataclass
class ADTConfig:
    """Global ADT configuration."""

    # Default profile name when none specified
    default_profile: str = ""

    # Base directory for profile lookup by name
    # e.g., ~/projects/project-profiles -> "adt seed -p python" finds python/ there
    profiles_dir: Path | None = None

    # Global variable defaults
    variables: dict[str, str] = field(default_factory=dict)

    # Behavior settings
    confirm_scripts: bool = True

    # Path to the config file that was loaded (for reference)
    config_path: Path | None = None

    def get_profile_path(self, name_or_path: str) -> Path | None:
        """Get the path to a profile by name or path.

        Args:
            name_or_path: Profile name or direct path to profile directory

        Returns:
            Path to the profile directory, or None if not found
        """
        # If it looks like a path (contains / or starts with . or ~), treat as path
        if "/" in name_or_path or name_or_path.startswith((".", "~")):
            path = Path(name_or_path).expanduser().resolve()
            if path.exists() and path.is_dir():
                return path
            return None

        # Otherwise, look up by name in profiles_dir
        if self.profiles_dir:
            profile_path = self.profiles_dir / name_or_path
            if profile_path.exists() and profile_path.is_dir():
                return profile_path

        return None

    def list_profiles(self) -> list[str]:
        """List all available profile names from profiles_dir.

        Returns:
            List of profile names
        """
        profiles: set[str] = set()

        if self.profiles_dir and self.profiles_dir.exists():
            for path in self.profiles_dir.iterdir():
                if path.is_dir() and (path / "profile.toml").exists():
                    profiles.add(path.name)

        return sorted(profiles)


def load_config(
    config_path: Path | None = None,
    project_dir: Path | None = None,
) -> ADTConfig:
    """Load ADT configuration with hierarchical merging.

    Configuration sources (in priority order, lowest to highest):
    1. ~/.config/adt/config.toml (global defaults)
    2. .adt-config.toml in project_dir (project overrides)
    3. Explicit config_path if provided (overrides all)

    Args:
        config_path: Explicit config file path (overrides hierarchy)
        project_dir: Project directory for .adt-config.toml lookup (default: cwd)

    Returns:
        ADTConfig instance with merged values
    """
    config = ADTConfig()
    project_dir = project_dir or Path.cwd()

    # If explicit config path provided, use only that
    if config_path is not None:
        config.config_path = config_path
        _load_config_file(config, config_path)
        return config

    # Otherwise, load hierarchically
    # 1. Global config
    if GLOBAL_CONFIG_FILE.exists():
        _load_config_file(config, GLOBAL_CONFIG_FILE)
        config.config_path = GLOBAL_CONFIG_FILE

    # 2. Project config (overrides global)
    project_config = project_dir / PROJECT_CONFIG_FILE
    if project_config.exists():
        _load_config_file(config, project_config)
        config.config_path = project_config

    return config


def _load_config_file(config: ADTConfig, config_path: Path) -> None:
    """Load and merge a config file into an ADTConfig instance.

    Args:
        config: Config instance to update
        config_path: Path to TOML config file
    """
    try:
        content = config_path.read_text()
        data = tomlkit.parse(content)
    except Exception as e:
        print(f"Warning: Failed to parse config file {config_path}: {e}")
        return

    # Load seed-specific settings
    if "seed" in data:
        seed = data["seed"]
        if "default_profile" in seed:
            config.default_profile = str(seed["default_profile"])
        if "profiles_dir" in seed:
            config.profiles_dir = Path(str(seed["profiles_dir"])).expanduser()

    # Load variables (merged, not replaced)
    if "variables" in data:
        for name, value in data["variables"].items():
            config.variables[name] = str(value)

    # Load settings
    if "settings" in data:
        settings = data["settings"]
        if "confirm_scripts" in settings:
            config.confirm_scripts = bool(settings["confirm_scripts"])


def ensure_config_dir() -> Path:
    """Ensure the global config directory exists.

    Returns:
        Path to the config directory
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return GLOBAL_CONFIG_DIR


def get_default_config_template() -> str:
    """Get a template for a new config file.

    Returns:
        TOML string with commented example configuration
    """
    return """\
# ADT Configuration
# Global: ~/.config/adt/config.toml
# Project: .adt-config.toml

# Seed command settings
[seed]
# Default profile when none specified
# default_profile = "python"

# Base directory for profile lookup by name
# With this set, "adt seed -p python" looks for python/ in this directory
# profiles_dir = "~/projects/project-profiles"

# Global variable defaults (lowest priority)
[variables]
# author = "Your Name"
# email = "you@example.com"
# license = "MIT"

# Behavior settings
[settings]
# confirm_scripts = true
"""
