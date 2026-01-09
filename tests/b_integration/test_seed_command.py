# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Integration tests for the seed command."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from abilian_devtools.commands.seed import SeedCommand
from abilian_devtools.seed.config import ADTConfig


def create_seed_command():
    """Create a SeedCommand with a mock CLI."""
    mock_cli = MagicMock()
    return SeedCommand(mock_cli)


@pytest.fixture
def restore_cwd():
    """Fixture to restore working directory after test."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)


@pytest.mark.integration
@pytest.mark.usefixtures("restore_cwd")
class TestSeedCommandBuiltin:
    """Tests for seed command with built-in templates."""

    def test_seed_builtin_creates_files(self):
        """Test that seed creates files from built-in templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Mock load_config to return empty config (triggers builtin fallback)
            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = ADTConfig()

                cmd = create_seed_command()
                cmd.run([])

            # Check that at least some files were created
            created_files = list(Path(tmpdir).iterdir())
            assert len(created_files) > 0

    def test_seed_builtin_dry_run(self):
        """Test that dry run doesn't create files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = ADTConfig()

                cmd = create_seed_command()
                cmd.run(["dry"])

            # No files should be created
            created_files = [f for f in Path(tmpdir).iterdir() if f.name != "."]
            # Only directories might be empty
            assert all(f.is_dir() for f in created_files) or len(created_files) == 0

    def test_seed_builtin_skips_existing_files(self, capsys):
        """Test that existing files are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)

            # Create an existing file
            existing = Path(tmpdir) / ".gitignore"
            existing.write_text("existing content")

            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = ADTConfig()

                cmd = create_seed_command()
                cmd.run([])

            # File should still have original content
            assert existing.read_text() == "existing content"

            # Should show skip message
            captured = capsys.readouterr()
            assert "skip" in captured.out


@pytest.mark.integration
@pytest.mark.usefixtures("restore_cwd")
class TestSeedCommandWithProfile:
    """Tests for seed command with profile-based seeding."""

    @pytest.fixture
    def profile_setup(self):
        """Create a temporary profile and project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create profile directory
            profile_dir = tmpdir / "profiles" / "test-profile"
            profile_dir.mkdir(parents=True)

            # Create profile.toml
            (profile_dir / "profile.toml").write_text("""
[profile]
name = "test-profile"
description = "A test profile"
version = "1.0.0"

[variables]
author = "Test Author"
year = 2025
""")

            # Create templates directory
            templates_dir = profile_dir / "templates"
            templates_dir.mkdir()

            # Create a plain template
            (templates_dir / "README.txt").write_text("Plain readme")

            # Create a Jinja2 template
            (templates_dir / "LICENSE.j2").write_text("""
Copyright {{ year }} {{ author }}
MIT License
""")

            # Create project directory
            project_dir = tmpdir / "project"
            project_dir.mkdir()

            # Create config
            config = ADTConfig(sources={"test-profile": str(profile_dir)})

            yield {
                "profile_dir": profile_dir,
                "project_dir": project_dir,
                "config": config,
            }

    def test_seed_with_profile(self, profile_setup, capsys):
        """Test seeding with a profile creates expected files."""
        project_dir = profile_setup["project_dir"]
        config = profile_setup["config"]

        os.chdir(project_dir)

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["test-profile"])

        # Check files were created
        assert (project_dir / "README.txt").exists()
        assert (project_dir / "LICENSE").exists()  # .j2 stripped

        # Check plain file content
        assert (project_dir / "README.txt").read_text() == "Plain readme"

        # Check rendered template content
        license_content = (project_dir / "LICENSE").read_text()
        assert "2025" in license_content
        assert "Test Author" in license_content

    def test_seed_with_profile_dry_run(self, profile_setup, capsys):
        """Test dry run with profile shows what would be done."""
        project_dir = profile_setup["project_dir"]
        config = profile_setup["config"]

        os.chdir(project_dir)

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["test-profile", "dry"])

        # Files should not be created
        assert not (project_dir / "README.txt").exists()
        assert not (project_dir / "LICENSE").exists()

        # Should show "would create" messages
        captured = capsys.readouterr()
        assert "would create" in captured.out

    def test_seed_with_profile_overwrite(self, profile_setup):
        """Test overwrite mode replaces existing files."""
        project_dir = profile_setup["project_dir"]
        config = profile_setup["config"]

        os.chdir(project_dir)

        # Create existing file
        (project_dir / "README.txt").write_text("old content")

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["test-profile", "force"])  # force = overwrite + yes

        # File should have new content
        assert (project_dir / "README.txt").read_text() == "Plain readme"

    def test_seed_list_profiles(self, profile_setup, capsys):
        """Test listing available profiles."""
        config = profile_setup["config"]

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["list"])

        captured = capsys.readouterr()
        assert "test-profile" in captured.out
        assert "A test profile" in captured.out

    def test_seed_info_profile(self, profile_setup, capsys):
        """Test showing profile information."""
        config = profile_setup["config"]

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["info", "test-profile"])

        captured = capsys.readouterr()
        assert "test-profile" in captured.out
        assert "A test profile" in captured.out
        assert "author" in captured.out
        assert "Test Author" in captured.out


@pytest.mark.integration
@pytest.mark.usefixtures("restore_cwd")
class TestSeedCommandWithInheritance:
    """Tests for seed command with profile inheritance."""

    @pytest.fixture
    def inheritance_setup(self):
        """Create profiles with inheritance chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create base profile
            base_dir = tmpdir / "profiles" / "base"
            base_dir.mkdir(parents=True)
            (base_dir / "profile.toml").write_text("""
[profile]
name = "base"

[variables]
license = "MIT"
""")
            (base_dir / "templates").mkdir()
            (base_dir / "templates" / "base.txt").write_text("from base")

            # Create child profile
            child_dir = tmpdir / "profiles" / "child"
            child_dir.mkdir(parents=True)
            (child_dir / "profile.toml").write_text("""
[profile]
name = "child"
extends = ["base"]

[variables]
author = "Child Author"
""")
            (child_dir / "templates").mkdir()
            (child_dir / "templates" / "child.txt").write_text("from child")

            # Create project directory
            project_dir = tmpdir / "project"
            project_dir.mkdir()

            config = ADTConfig(
                sources={
                    "base": str(base_dir),
                    "child": str(child_dir),
                }
            )

            yield {
                "base_dir": base_dir,
                "child_dir": child_dir,
                "project_dir": project_dir,
                "config": config,
            }

    def test_seed_with_inheritance(self, inheritance_setup):
        """Test seeding with inherited profile includes base files."""
        project_dir = inheritance_setup["project_dir"]
        config = inheritance_setup["config"]

        os.chdir(project_dir)

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["child"])

        # Both base and child files should be created
        assert (project_dir / "base.txt").exists()
        assert (project_dir / "child.txt").exists()


@pytest.mark.integration
@pytest.mark.usefixtures("restore_cwd")
class TestSeedCommandVariableResolution:
    """Tests for variable resolution in seed command."""

    @pytest.fixture
    def variable_setup(self):
        """Create a profile with various template variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create profile
            profile_dir = tmpdir / "profiles" / "vars"
            profile_dir.mkdir(parents=True)
            (profile_dir / "profile.toml").write_text("""
[profile]
name = "vars"

[variables]
profile_var = "from_profile"
""")
            (profile_dir / "templates").mkdir()
            (profile_dir / "templates" / "vars.txt.j2").write_text("""
Project: {{ project_name }}
Version: {{ project_version }}
Year: {{ current_year }}
Profile Var: {{ profile_var }}
Has Src: {{ has_src_layout }}
""")

            # Create project directory with pyproject.toml
            project_dir = tmpdir / "project"
            project_dir.mkdir()
            (project_dir / "pyproject.toml").write_text("""
[project]
name = "my-awesome-project"
version = "2.5.0"
""")
            (project_dir / "src").mkdir()

            config = ADTConfig(sources={"vars": str(profile_dir)})

            yield {
                "profile_dir": profile_dir,
                "project_dir": project_dir,
                "config": config,
            }

    def test_seed_resolves_all_variables(self, variable_setup):
        """Test that all variable sources are resolved correctly."""
        project_dir = variable_setup["project_dir"]
        config = variable_setup["config"]

        os.chdir(project_dir)

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(["vars"])

        content = (project_dir / "vars.txt").read_text()

        # Check computed variables
        assert "Project: my-awesome-project" in content
        assert "Version: 2.5.0" in content
        assert f"Year: {2025}" in content or f"Year: {2026}" in content  # Current year

        # Check profile variable
        assert "Profile Var: from_profile" in content

        # Check layout detection
        assert "Has Src: True" in content


@pytest.mark.integration
@pytest.mark.usefixtures("restore_cwd")
class TestSeedCommandNestedTemplates:
    """Tests for nested template directories."""

    def test_seed_creates_nested_directories(self):
        """Test that nested template directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create profile with nested templates
            profile_dir = tmpdir / "profiles" / "nested"
            profile_dir.mkdir(parents=True)
            (profile_dir / "profile.toml").write_text("""
[profile]
name = "nested"
""")

            templates_dir = profile_dir / "templates"
            templates_dir.mkdir()
            (templates_dir / "root.txt").write_text("root file")
            (templates_dir / "subdir").mkdir()
            (templates_dir / "subdir" / "nested.txt").write_text("nested file")
            (templates_dir / "subdir" / "deep").mkdir()
            (templates_dir / "subdir" / "deep" / "deep.txt").write_text("deep file")

            # Create project directory
            project_dir = tmpdir / "project"
            project_dir.mkdir()

            config = ADTConfig(sources={"nested": str(profile_dir)})

            os.chdir(project_dir)

            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = config

                cmd = create_seed_command()
                cmd.run(["nested"])

            # Check all files were created with correct structure
            assert (project_dir / "root.txt").exists()
            assert (project_dir / "subdir" / "nested.txt").exists()
            assert (project_dir / "subdir" / "deep" / "deep.txt").exists()
