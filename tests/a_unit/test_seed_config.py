# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Unit tests for seed configuration module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from abilian_devtools.seed.config import ADTConfig, load_config

# =============================================================================
# Tests for ADTConfig defaults
# =============================================================================


@pytest.mark.unit
class TestADTConfigDefaults:
    """Tests for ADTConfig default values."""

    def test_default_profile_returns_empty_string(self):
        # Arrange
        config = ADTConfig()

        # Assert
        assert config.default_profile == ""

    def test_profiles_dir_returns_none(self):
        # Arrange
        config = ADTConfig()

        # Assert
        assert config.profiles_dir is None

    def test_variables_returns_empty_dict(self):
        # Arrange
        config = ADTConfig()

        # Assert
        assert config.variables == {}

    def test_confirm_scripts_returns_true(self):
        # Arrange
        config = ADTConfig()

        # Assert
        assert config.confirm_scripts is True


# =============================================================================
# Tests for ADTConfig.list_profiles
# =============================================================================


@pytest.mark.unit
class TestADTConfigListProfiles:
    """Tests for ADTConfig.list_profiles method."""

    def test_list_profiles_returns_empty_when_no_profiles_dir(self):
        # Arrange
        config = ADTConfig()

        # Act
        profiles = config.list_profiles()

        # Assert
        assert profiles == []

    def test_list_profiles_finds_directories_with_profile_toml(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)

            # Create profile directories
            (profiles_dir / "python").mkdir()
            (profiles_dir / "python" / "profile.toml").write_text("[profile]")
            (profiles_dir / "web").mkdir()
            (profiles_dir / "web" / "profile.toml").write_text("[profile]")

            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            profiles = config.list_profiles()

            # Assert
            assert "python" in profiles
            assert "web" in profiles

    def test_list_profiles_ignores_files(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)

            # Create a file (not a directory)
            (profiles_dir / "not-a-profile.txt").write_text("content")

            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            profiles = config.list_profiles()

            # Assert
            assert "not-a-profile.txt" not in profiles

    def test_list_profiles_ignores_dirs_without_profile_toml(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)

            # Create directory without profile.toml
            (profiles_dir / "incomplete").mkdir()

            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            profiles = config.list_profiles()

            # Assert
            assert "incomplete" not in profiles


# =============================================================================
# Tests for ADTConfig.get_profile_path
# =============================================================================


@pytest.mark.unit
class TestADTConfigGetProfilePath:
    """Tests for ADTConfig.get_profile_path method."""

    def test_get_profile_path_returns_path_from_profiles_dir(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir)
            python_dir = profiles_dir / "python"
            python_dir.mkdir()

            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            result = config.get_profile_path("python")

            # Assert
            assert result == python_dir

    def test_get_profile_path_returns_none_for_unknown_profile(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ADTConfig(profiles_dir=Path(tmpdir))

            # Act
            result = config.get_profile_path("nonexistent")

            # Assert
            assert result is None

    def test_get_profile_path_handles_direct_path(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_dir = Path(tmpdir).resolve() / "my-profile"
            profile_dir.mkdir()

            config = ADTConfig()  # No profiles_dir set

            # Act
            result = config.get_profile_path(str(profile_dir))

            # Assert
            assert result == profile_dir

    def test_get_profile_path_expands_tilde(self):
        # Arrange
        config = ADTConfig()

        # Act - using home directory which should exist
        result = config.get_profile_path("~")

        # Assert
        assert result == Path.home()

    def test_get_profile_path_returns_none_for_nonexistent_path(self):
        # Arrange
        config = ADTConfig()

        # Act
        result = config.get_profile_path("/nonexistent/path/to/profile")

        # Assert
        assert result is None


# =============================================================================
# Tests for load_config
# =============================================================================


@pytest.mark.unit
class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_returns_defaults_when_no_config_exists(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the global config file to a non-existent path
            fake_global = Path(tmpdir) / "nonexistent" / "config.toml"
            with patch(
                "abilian_devtools.seed.config.GLOBAL_CONFIG_FILE", fake_global
            ):
                # Act - load config with non-existent paths
                config = load_config(project_dir=Path(tmpdir))

                # Assert - should have defaults
                assert config.default_profile == ""
                assert config.profiles_dir is None
                assert config.variables == {}

    def test_load_config_reads_explicit_config_path(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("""
[seed]
default_profile = "python"
profiles_dir = "~/my-profiles"

[variables]
author = "Test Author"
""")

            # Act
            config = load_config(config_path=config_file)

            # Assert
            assert config.default_profile == "python"
            assert config.profiles_dir == Path.home() / "my-profiles"
            assert config.variables["author"] == "Test Author"

    def test_load_config_reads_project_config(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            project_config = project_dir / ".adt-config.toml"
            project_config.write_text("""
[seed]
default_profile = "web"

[variables]
project_var = "from_project"
""")

            # Act
            config = load_config(project_dir=project_dir)

            # Assert
            assert config.default_profile == "web"
            assert config.variables["project_var"] == "from_project"

    def test_load_config_merges_variables(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("""
[variables]
author = "Test Author"
license = "MIT"
""")

            # Act
            config = load_config(config_path=config_file)

            # Assert
            assert config.variables["author"] == "Test Author"
            assert config.variables["license"] == "MIT"

    def test_load_config_reads_settings(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("""
[settings]
confirm_scripts = false
""")

            # Act
            config = load_config(config_path=config_file)

            # Assert
            assert config.confirm_scripts is False

    def test_load_config_handles_empty_file(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("")

            # Act
            config = load_config(config_path=config_file)

            # Assert - should have defaults
            assert config.default_profile == ""

    def test_load_config_handles_invalid_toml(self, capsys):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.toml"
            config_file.write_text("invalid [ toml content")

            # Act
            config = load_config(config_path=config_file)

            # Assert - should return defaults with warning
            assert config.default_profile == ""
            captured = capsys.readouterr()
            assert "Warning" in captured.out
