# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT
"""Variable resolution for seed templates.

Variables are resolved in priority order (highest first):
1. CLI arguments
2. Environment variables (ADT_VAR_*)
3. Profile variables (later profiles override earlier)
4. Project pyproject.toml values
5. Global config variables
6. Computed values (project_name, current_year, etc.)
"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from importlib.metadata import version as get_package_version
from pathlib import Path
from typing import Any

import tomlkit

from .config import ADTConfig
from .profile import Profile


@dataclass
class VariableResolver:
    """Resolves variables from multiple sources."""

    # CLI-provided variables (highest priority)
    cli_vars: dict[str, Any] = field(default_factory=dict)

    # Profiles (in resolution order, later overrides earlier)
    profiles: list[Profile] = field(default_factory=list)

    # Global config
    config: ADTConfig | None = None

    # Project directory
    project_dir: Path = field(default_factory=Path.cwd)

    # Cached pyproject.toml data
    _pyproject_data: dict | None = field(default=None, repr=False)

    def resolve(self) -> dict[str, Any]:
        """Resolve all variables into a single context dict.

        Returns:
            Dictionary with all resolved variables
        """
        context: dict[str, Any] = {}

        # Layer 6: Computed values (lowest priority)
        context.update(self._get_computed_vars())

        # Layer 5: Global config variables
        if self.config:
            context.update(self.config.variables)

        # Layer 4: Project pyproject.toml values
        context.update(self._get_pyproject_vars())

        # Layer 3: Profile variables (in order, later overrides)
        for profile in self.profiles:
            context.update(profile.variables)

        # Layer 2: Environment variables (ADT_VAR_*)
        context.update(self._get_env_vars())

        # Layer 1: CLI variables (highest priority)
        context.update(self.cli_vars)

        # Add special objects
        context["project"] = self._get_pyproject_data()
        context["env"] = dict(os.environ)
        context["adt"] = self._get_adt_metadata()

        return context

    def _get_computed_vars(self) -> dict[str, Any]:
        """Get auto-computed variables.

        Returns:
            Dictionary of computed variable values
        """
        project_data = self._get_pyproject_data()

        # Project name: from pyproject.toml or directory name
        project_name = ""
        if project_data and "project" in project_data:
            project_name = project_data["project"].get("name", "")
        if not project_name:
            project_name = self.project_dir.name

        # Project version
        project_version = "0.1.0"
        if project_data and "project" in project_data:
            project_version = project_data["project"].get("version", project_version)

        # Project description
        project_description = ""
        if project_data and "project" in project_data:
            project_description = project_data["project"].get("description", "")

        # Python version from pyproject.toml or .python-version
        python_version = self._detect_python_version()

        # Layout detection
        has_src_layout = (self.project_dir / "src").is_dir()
        has_tests = (self.project_dir / "tests").is_dir()

        return {
            "project_name": project_name,
            "project_version": project_version,
            "project_description": project_description,
            "python_version": python_version,
            "has_src_layout": has_src_layout,
            "has_tests": has_tests,
            "current_year": datetime.now().year,
            "project_dir": str(self.project_dir),
        }

    def _get_pyproject_vars(self) -> dict[str, Any]:
        """Get variables from project's pyproject.toml [tool.adt] section.

        Returns:
            Dictionary of variables from pyproject.toml
        """
        data = self._get_pyproject_data()
        if not data:
            return {}

        # Get variables from [tool.adt.variables]
        tool_adt = data.get("tool", {}).get("adt", {})
        return dict(tool_adt.get("variables", {}))

    def _get_env_vars(self) -> dict[str, Any]:
        """Get variables from environment (ADT_VAR_* prefix).

        Returns:
            Dictionary of environment variables with prefix stripped
        """
        prefix = "ADT_VAR_"
        result = {}

        for key, value in os.environ.items():
            if key.startswith(prefix):
                var_name = key[len(prefix) :].lower()
                result[var_name] = value

        return result

    def _get_pyproject_data(self) -> dict:
        """Load and cache pyproject.toml data.

        Returns:
            Parsed pyproject.toml as dictionary, or empty dict if not found
        """
        if self._pyproject_data is not None:
            return self._pyproject_data

        pyproject_path = self.project_dir / "pyproject.toml"
        if not pyproject_path.exists():
            self._pyproject_data = {}
            return self._pyproject_data

        try:
            content = pyproject_path.read_text()
            self._pyproject_data = dict(tomlkit.parse(content))
        except Exception:
            self._pyproject_data = {}

        return self._pyproject_data

    def _get_adt_metadata(self) -> dict[str, Any]:
        """Get ADT metadata for templates.

        Returns:
            Dictionary with ADT version and profile info
        """
        try:
            adt_version = get_package_version("abilian-devtools")
        except Exception:
            adt_version = "unknown"

        return {
            "version": adt_version,
            "profiles": [p.name for p in self.profiles],
        }

    def _detect_python_version(self) -> str:
        """Detect Python version from project configuration.

        Returns:
            Python version string (e.g., "3.12")
        """
        # Try .python-version file
        python_version_file = self.project_dir / ".python-version"
        if python_version_file.exists():
            version = python_version_file.read_text().strip()
            # Extract major.minor from version string
            parts = version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"

        # Try pyproject.toml requires-python
        data = self._get_pyproject_data()
        if data and "project" in data:
            requires_python = data["project"].get("requires-python", "")
            # Parse something like ">=3.10,<4.0" or ">=3.12"
            if requires_python:
                # Extract first version number
                match = re.search(r"(\d+\.\d+)", requires_python)
                if match:
                    return match.group(1)

        # Default
        return "3.12"


def parse_cli_vars(var_args: list[str]) -> dict[str, Any]:
    """Parse CLI variable arguments.

    Args:
        var_args: List of "name=value" strings

    Returns:
        Dictionary of parsed variables
    """
    result = {}

    for arg in var_args:
        if "=" not in arg:
            continue

        name, value = arg.split("=", 1)
        name = name.strip()
        value = value.strip()

        # Try to parse as bool/int/float
        result[name] = _parse_value(value)

    return result


def _parse_value(value: str) -> Any:
    """Parse a string value into appropriate type.

    Args:
        value: String value to parse

    Returns:
        Parsed value (bool, int, float, or str)
    """
    # Boolean
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False

    # Integer
    try:
        return int(value)
    except ValueError:
        pass

    # Float
    try:
        return float(value)
    except ValueError:
        pass

    # String (strip quotes if present)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    return value
