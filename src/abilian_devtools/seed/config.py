# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Global ADT configuration management.

Handles loading and managing the global ADT configuration from
~/.config/adt/config.toml
"""

from dataclasses import dataclass, field
from pathlib import Path

import tomlkit

# Default config directory
CONFIG_DIR = Path.home() / ".config" / "adt"
CONFIG_FILE = CONFIG_DIR / "config.toml"
PROFILES_DIR = CONFIG_DIR / "profiles"


@dataclass
class ADTConfig:
    """Global ADT configuration."""

    # Default profile name when none specified
    default_profile: str = ""

    # Profile sources: name -> path or git URL
    sources: dict[str, str] = field(default_factory=dict)

    # Global variable defaults
    variables: dict[str, str] = field(default_factory=dict)

    # Behavior settings
    confirm_scripts: bool = True
    cache_git_profiles: bool = True
    cache_dir: Path = field(
        default_factory=lambda: Path.home() / ".cache" / "adt" / "profiles"
    )

    # Path to profiles directory (for test isolation)
    profiles_dir: Path = field(default_factory=lambda: PROFILES_DIR)

    # Path to the config file (for reference)
    config_path: Path | None = None

    def get_profile_path(self, name: str) -> Path | None:
        """Get the path to a profile by name.

        Args:
            name: Profile name to look up

        Returns:
            Path to the profile directory, or None if not found
        """
        # Check explicit sources first
        if name in self.sources:
            source = self.sources[name]
            # For now, only handle local paths (git support in later phase)
            path = Path(source).expanduser()
            if path.exists():
                return path

        # Check profiles directory
        profile_path = self.profiles_dir / name
        if profile_path.exists():
            return profile_path

        return None

    def list_profiles(self) -> list[str]:
        """List all available profile names.

        Returns:
            List of profile names from sources and profiles directory
        """
        profiles = set(self.sources.keys())

        # Add profiles from profiles directory
        if self.profiles_dir.exists():
            for path in self.profiles_dir.iterdir():
                if path.is_dir() and (path / "profile.toml").exists():
                    profiles.add(path.name)

        return sorted(profiles)


def load_config(
    config_path: Path | None = None,
    config_dir: Path | None = None,
) -> ADTConfig:
    """Load ADT configuration from file.

    Args:
        config_path: Optional path to config file. Defaults to ~/.config/adt/config.toml
        config_dir: Optional config directory (for testing). If provided, looks for
                    config.toml in this directory and uses its profiles/ subdirectory.

    Returns:
        ADTConfig instance with loaded or default values
    """
    if config_dir is not None:
        config_path = config_dir / "config.toml"
        profiles_dir = config_dir / "profiles"
    elif config_path is None:
        config_path = CONFIG_FILE
        profiles_dir = PROFILES_DIR
    else:
        profiles_dir = config_path.parent / "profiles"

    config = ADTConfig(config_path=config_path, profiles_dir=profiles_dir)

    if not config_path.exists():
        return config

    try:
        content = config_path.read_text()
        data = tomlkit.parse(content)
    except Exception as e:
        print(f"Warning: Failed to parse config file {config_path}: {e}")
        return config

    # Load default profile
    if "default_profile" in data:
        config.default_profile = str(data["default_profile"])

    # Load sources
    if "sources" in data:
        for name, source in data["sources"].items():
            config.sources[name] = str(source)

    # Load variables
    if "variables" in data:
        for name, value in data["variables"].items():
            config.variables[name] = str(value)

    # Load settings
    if "settings" in data:
        settings = data["settings"]
        if "confirm_scripts" in settings:
            config.confirm_scripts = bool(settings["confirm_scripts"])
        if "cache_git_profiles" in settings:
            config.cache_git_profiles = bool(settings["cache_git_profiles"])
        if "cache_dir" in settings:
            config.cache_dir = Path(str(settings["cache_dir"])).expanduser()

    return config


def ensure_config_dir() -> Path:
    """Ensure the config directory exists.

    Returns:
        Path to the config directory
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def ensure_profiles_dir() -> Path:
    """Ensure the profiles directory exists.

    Returns:
        Path to the profiles directory
    """
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def get_default_config_template() -> str:
    """Get a template for a new config file.

    Returns:
        TOML string with commented example configuration
    """
    return """\
# ADT Configuration
# Location: ~/.config/adt/config.toml

# Default profile when none specified
# default_profile = "python"

# Profile sources - local paths or git URLs
# [sources]
# python = "~/.config/adt/profiles/python"
# web = "~/.config/adt/profiles/web"
# company = "git@github.com:mycompany/adt-profiles.git#main:profiles"

# Global variable defaults (lowest priority)
# [variables]
# author = "Your Name"
# email = "you@example.com"
# license = "MIT"

# Behavior settings
# [settings]
# confirm_scripts = true
# cache_git_profiles = true
# cache_dir = "~/.cache/adt/profiles"
"""
