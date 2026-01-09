# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Unit tests for seed config module."""

import tempfile
from pathlib import Path

import pytest

from abilian_devtools.seed.config import ADTConfig, load_config


@pytest.mark.unit
class TestADTConfigDefaults:
    """Tests for ADTConfig default values."""

    def test_default_profile_returns_empty_string(self):
        # Arrange
        config = ADTConfig()

        # Assert
        assert config.default_profile == ""

    def test_sources_returns_empty_dict(self):
        # Arrange
        config = ADTConfig()

        # Assert
        assert config.sources == {}

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


@pytest.mark.unit
class TestADTConfigListProfiles:
    """Tests for ADTConfig.list_profiles method."""

    def test_list_profiles_returns_empty_when_no_sources_exist(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ADTConfig(profiles_dir=Path(tmpdir) / "nonexistent")

            # Act
            profiles = config.list_profiles()

            # Assert
            assert profiles == []

    def test_list_profiles_returns_source_names(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ADTConfig(
                sources={
                    "profile1": "/path/to/profile1",
                    "profile2": "/path/to/profile2",
                },
                profiles_dir=Path(tmpdir) / "nonexistent",
            )

            # Act
            profiles = config.list_profiles()

            # Assert
            assert set(profiles) == {"profile1", "profile2"}

    def test_list_profiles_finds_directories_with_profile_toml(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "web").mkdir()
            (profiles_dir / "web" / "profile.toml").write_text(
                "[profile]\nname = 'web'"
            )
            (profiles_dir / "python").mkdir()
            (profiles_dir / "python" / "profile.toml").write_text(
                "[profile]\nname = 'python'"
            )
            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            profiles = config.list_profiles()

            # Assert
            assert set(profiles) == {"web", "python"}

    def test_list_profiles_ignores_files(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "readme.txt").write_text("not a profile")
            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            profiles = config.list_profiles()

            # Assert
            assert profiles == []

    def test_list_profiles_combines_sources_and_directory(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "local-profile").mkdir()
            (profiles_dir / "local-profile" / "profile.toml").write_text(
                "[profile]\nname = 'local'"
            )
            config = ADTConfig(
                sources={"remote-profile": "/path/to/remote"},
                profiles_dir=profiles_dir,
            )

            # Act
            profiles = config.list_profiles()

            # Assert
            assert set(profiles) == {"local-profile", "remote-profile"}


@pytest.mark.unit
class TestADTConfigGetProfilePath:
    """Tests for ADTConfig.get_profile_path method."""

    def test_get_profile_path_returns_path_from_sources(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "my-profile"
            profile_path.mkdir()
            config = ADTConfig(
                sources={"my-profile": str(profile_path)},
                profiles_dir=Path(tmpdir) / "nonexistent",
            )

            # Act
            result = config.get_profile_path("my-profile")

            # Assert
            assert result == profile_path

    def test_get_profile_path_returns_path_from_profiles_dir(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            profile_path = profiles_dir / "my-profile"
            profile_path.mkdir()
            config = ADTConfig(profiles_dir=profiles_dir)

            # Act
            result = config.get_profile_path("my-profile")

            # Assert
            assert result == profile_path

    def test_get_profile_path_returns_none_for_unknown_profile(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ADTConfig(profiles_dir=Path(tmpdir) / "nonexistent")

            # Act
            result = config.get_profile_path("nonexistent")

            # Assert
            assert result is None

    def test_get_profile_path_prefers_sources_over_profiles_dir(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()
            (profiles_dir / "my-profile").mkdir()
            override_path = Path(tmpdir) / "override"
            override_path.mkdir()
            config = ADTConfig(
                sources={"my-profile": str(override_path)},
                profiles_dir=profiles_dir,
            )

            # Act
            result = config.get_profile_path("my-profile")

            # Assert
            assert result == override_path


@pytest.mark.unit
class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_returns_defaults_when_file_missing(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert isinstance(config, ADTConfig)
            assert config.default_profile == ""

    def test_load_config_handles_empty_file(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"
            config_dir.mkdir(parents=True)
            (config_dir / "config.toml").write_text("")

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert isinstance(config, ADTConfig)

    def test_load_config_reads_default_profile(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"
            config_dir.mkdir(parents=True)
            (config_dir / "config.toml").write_text('default_profile = "my-default"')

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert config.default_profile == "my-default"

    def test_load_config_reads_sources_section(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"
            config_dir.mkdir(parents=True)
            (config_dir / "config.toml").write_text(
                '[sources]\npython = "/path/to/python"'
            )

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert config.sources["python"] == "/path/to/python"

    def test_load_config_reads_variables_section(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"
            config_dir.mkdir(parents=True)
            (config_dir / "config.toml").write_text(
                '[variables]\nauthor = "Test Author"'
            )

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert config.variables["author"] == "Test Author"

    def test_load_config_sets_profiles_dir_from_config_dir(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"
            config_dir.mkdir(parents=True)
            profiles_dir = config_dir / "profiles"
            profiles_dir.mkdir()
            (config_dir / "config.toml").write_text("")

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert config.profiles_dir == profiles_dir

    def test_load_config_reads_settings_confirm_scripts(self):
        # Arrange
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "adt"
            config_dir.mkdir(parents=True)
            (config_dir / "profiles").mkdir()
            (config_dir / "config.toml").write_text(
                "[settings]\nconfirm_scripts = false"
            )

            # Act
            config = load_config(config_dir=config_dir)

            # Assert
            assert config.confirm_scripts is False
