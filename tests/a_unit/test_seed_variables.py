# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Unit tests for seed variables module."""

import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from abilian_devtools.seed.config import ADTConfig
from abilian_devtools.seed.profile import Profile
from abilian_devtools.seed.variables import VariableResolver, parse_cli_vars


@pytest.mark.unit
class TestVariableResolver:
    """Tests for VariableResolver class."""

    def test_resolve_computed_vars_basic(self):
        """Test basic computed variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()

            # Check computed values
            assert context["current_year"] == datetime.now().year
            assert context["project_dir"] == str(project_dir)
            assert context["project_name"] == project_dir.name
            assert context["python_version"]  # Should have some value

    def test_resolve_from_pyproject(self):
        """Test variable resolution from pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text("""
[project]
name = "my-project"
version = "1.2.3"
description = "A test project"
requires-python = ">=3.11"
""")

            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()

            assert context["project_name"] == "my-project"
            assert context["project_version"] == "1.2.3"
            assert context["project_description"] == "A test project"
            assert context["python_version"] == "3.11"

    def test_resolve_from_python_version_file(self):
        """Test Python version from .python-version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / ".python-version").write_text("3.12.1")

            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()

            assert context["python_version"] == "3.12"

    def test_resolve_layout_detection(self):
        """Test has_src_layout and has_tests detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            # No src or tests
            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()
            assert context["has_src_layout"] is False
            assert context["has_tests"] is False

            # Add src and tests directories
            (project_dir / "src").mkdir()
            (project_dir / "tests").mkdir()

            context = resolver.resolve()
            assert context["has_src_layout"] is True
            assert context["has_tests"] is True

    def test_resolve_from_config(self):
        """Test variable resolution from global config."""
        config = ADTConfig(
            variables={
                "author": "Config Author",
                "license": "MIT",
            }
        )

        resolver = VariableResolver(config=config)
        context = resolver.resolve()

        assert context["author"] == "Config Author"
        assert context["license"] == "MIT"

    def test_resolve_from_profile(self):
        """Test variable resolution from profile."""
        profile = Profile(
            name="test",
            variables={
                "author": "Profile Author",
                "framework": "flask",
            },
        )

        resolver = VariableResolver(profiles=[profile])
        context = resolver.resolve()

        assert context["author"] == "Profile Author"
        assert context["framework"] == "flask"

    def test_resolve_from_multiple_profiles(self):
        """Test variable resolution from multiple profiles (layering)."""
        base_profile = Profile(
            name="base",
            variables={
                "author": "Base Author",
                "version": "1.0",
            },
        )
        override_profile = Profile(
            name="override",
            variables={
                "author": "Override Author",  # Overrides base
                "extra": "value",
            },
        )

        resolver = VariableResolver(profiles=[base_profile, override_profile])
        context = resolver.resolve()

        # Later profile overrides earlier
        assert context["author"] == "Override Author"
        assert context["version"] == "1.0"  # From base
        assert context["extra"] == "value"  # From override

    def test_resolve_from_env_vars(self):
        """Test variable resolution from environment variables."""
        # Set environment variable with ADT_VAR_ prefix
        os.environ["ADT_VAR_AUTHOR"] = "Env Author"
        os.environ["ADT_VAR_PORT"] = "9000"

        try:
            resolver = VariableResolver()
            context = resolver.resolve()

            assert context["author"] == "Env Author"
            assert context["port"] == "9000"
        finally:
            # Cleanup
            del os.environ["ADT_VAR_AUTHOR"]
            del os.environ["ADT_VAR_PORT"]

    def test_resolve_from_cli_vars(self):
        """Test variable resolution from CLI arguments."""
        resolver = VariableResolver(
            cli_vars={
                "author": "CLI Author",
                "debug": True,
            }
        )
        context = resolver.resolve()

        assert context["author"] == "CLI Author"
        assert context["debug"] is True

    def test_resolve_priority_order(self):
        """Test that priority order is correct (CLI > env > profile > config > computed)."""
        # Set environment variable
        os.environ["ADT_VAR_AUTHOR"] = "Env Author"

        try:
            config = ADTConfig(variables={"author": "Config Author"})
            profile = Profile(name="test", variables={"author": "Profile Author"})

            # CLI should win
            resolver = VariableResolver(
                cli_vars={"author": "CLI Author"},
                profiles=[profile],
                config=config,
            )
            context = resolver.resolve()
            assert context["author"] == "CLI Author"

            # Without CLI, env should win
            resolver = VariableResolver(
                profiles=[profile],
                config=config,
            )
            context = resolver.resolve()
            assert context["author"] == "Env Author"

        finally:
            del os.environ["ADT_VAR_AUTHOR"]

        # Without env, profile should win
        resolver = VariableResolver(
            profiles=[profile],
            config=config,
        )
        context = resolver.resolve()
        assert context["author"] == "Profile Author"

        # Without profile, config should win
        resolver = VariableResolver(config=config)
        context = resolver.resolve()
        assert context["author"] == "Config Author"

    def test_resolve_special_objects(self):
        """Test that special objects (project, env, adt) are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text("""
[project]
name = "test-project"
version = "1.0.0"
""")

            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()

            # project object
            assert "project" in context
            assert context["project"]["project"]["name"] == "test-project"

            # env object
            assert "env" in context
            assert isinstance(context["env"], dict)
            assert "PATH" in context["env"]  # Should have PATH

            # adt object
            assert "adt" in context
            assert "version" in context["adt"]
            assert "profiles" in context["adt"]

    def test_resolve_pyproject_variables_section(self):
        """Test variable resolution from [tool.adt.variables] section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text("""
[project]
name = "test"

[tool.adt.variables]
custom_var = "custom_value"
another_var = "another_value"
""")

            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()

            assert context["custom_var"] == "custom_value"
            assert context["another_var"] == "another_value"

    def test_resolve_no_pyproject(self):
        """Test resolution when no pyproject.toml exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            # No pyproject.toml

            resolver = VariableResolver(project_dir=project_dir)
            context = resolver.resolve()

            # Should use directory name as project name
            assert context["project_name"] == project_dir.name
            # Should have default version
            assert context["project_version"] == "0.1.0"

    def test_resolve_caches_pyproject_data(self):
        """Test that pyproject data is cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            pyproject = project_dir / "pyproject.toml"
            pyproject.write_text("""
[project]
name = "cached-test"
""")

            resolver = VariableResolver(project_dir=project_dir)

            # Call resolve multiple times
            context1 = resolver.resolve()
            context2 = resolver.resolve()

            # Should return same data
            assert context1["project_name"] == context2["project_name"]


@pytest.mark.unit
class TestParseCLIVars:
    """Tests for parse_cli_vars function."""

    def test_parse_simple_string(self):
        """Test parsing simple string value."""
        result = parse_cli_vars(["name=value"])
        assert result == {"name": "value"}

    def test_parse_multiple_vars(self):
        """Test parsing multiple variables."""
        result = parse_cli_vars(["a=1", "b=2", "c=3"])
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_parse_boolean_true(self):
        """Test parsing boolean true values."""
        for val in ["true", "True", "TRUE", "yes", "YES", "1", "on"]:
            result = parse_cli_vars([f"flag={val}"])
            assert result["flag"] is True, f"Failed for {val}"

    def test_parse_boolean_false(self):
        """Test parsing boolean false values."""
        for val in ["false", "False", "FALSE", "no", "NO", "0", "off"]:
            result = parse_cli_vars([f"flag={val}"])
            assert result["flag"] is False, f"Failed for {val}"

    def test_parse_integer(self):
        """Test parsing integer values."""
        result = parse_cli_vars(["port=8080"])
        assert result["port"] == 8080
        assert isinstance(result["port"], int)

    def test_parse_negative_integer(self):
        """Test parsing negative integer."""
        result = parse_cli_vars(["offset=-10"])
        assert result["offset"] == -10

    def test_parse_float(self):
        """Test parsing float values."""
        result = parse_cli_vars(["ratio=3.14"])
        assert result["ratio"] == 3.14
        assert isinstance(result["ratio"], float)

    def test_parse_quoted_string(self):
        """Test parsing quoted string values."""
        result = parse_cli_vars(['name="quoted value"'])
        assert result["name"] == "quoted value"

    def test_parse_single_quoted_string(self):
        """Test parsing single-quoted string values."""
        result = parse_cli_vars(["name='single quoted'"])
        assert result["name"] == "single quoted"

    def test_parse_value_with_equals(self):
        """Test parsing value containing equals sign."""
        result = parse_cli_vars(["url=http://example.com?a=1&b=2"])
        assert result["url"] == "http://example.com?a=1&b=2"

    def test_parse_empty_list(self):
        """Test parsing empty list."""
        result = parse_cli_vars([])
        assert result == {}

    def test_parse_skips_invalid_format(self):
        """Test that invalid format entries are skipped."""
        result = parse_cli_vars(["valid=1", "invalid", "also-valid=2"])
        assert result == {"valid": 1, "also-valid": 2}

    def test_parse_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = parse_cli_vars(["  name  =  value  "])
        assert result["name"] == "value"
