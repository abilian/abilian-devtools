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
                cmd.run()

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
                cmd.run(dry_run=True)

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
                cmd.run()

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
            tmpdir = Path(tmpdir).resolve()

            # Create profiles directory with test-profile
            profiles_dir = tmpdir / "profiles"
            profile_dir = profiles_dir / "test-profile"
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

            # Create config with profiles_dir
            config = ADTConfig(profiles_dir=profiles_dir)

            yield {
                "profile_dir": profile_dir,
                "profiles_dir": profiles_dir,
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
            cmd.run(profile="test-profile")

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
            cmd.run(profile="test-profile", dry_run=True)

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
            cmd.run(profile="test-profile", overwrite=True, yes=True)

        # File should have new content
        assert (project_dir / "README.txt").read_text() == "Plain readme"

    def test_seed_list_profiles(self, profile_setup, capsys):
        """Test listing available profiles."""
        config = profile_setup["config"]

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(list=True)

        captured = capsys.readouterr()
        assert "test-profile" in captured.out
        assert "A test profile" in captured.out

    def test_seed_info_profile(self, profile_setup, capsys):
        """Test showing profile information."""
        config = profile_setup["config"]

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(info="test-profile")

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
            tmpdir = Path(tmpdir).resolve()

            # Create profiles directory
            profiles_dir = tmpdir / "profiles"

            # Create base profile
            base_dir = profiles_dir / "base"
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
            child_dir = profiles_dir / "child"
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

            config = ADTConfig(profiles_dir=profiles_dir)

            yield {
                "base_dir": base_dir,
                "child_dir": child_dir,
                "profiles_dir": profiles_dir,
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
            cmd.run(profile="child")

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
            tmpdir = Path(tmpdir).resolve()

            # Create profiles directory
            profiles_dir = tmpdir / "profiles"

            # Create profile
            profile_dir = profiles_dir / "vars"
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

            config = ADTConfig(profiles_dir=profiles_dir)

            yield {
                "profile_dir": profile_dir,
                "profiles_dir": profiles_dir,
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
            cmd.run(profile="vars")

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
            tmpdir = Path(tmpdir).resolve()

            # Create profiles directory
            profiles_dir = tmpdir / "profiles"

            # Create profile with nested templates
            profile_dir = profiles_dir / "nested"
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

            config = ADTConfig(profiles_dir=profiles_dir)

            os.chdir(project_dir)

            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = config

                cmd = create_seed_command()
                cmd.run(profile="nested")

            # Check all files were created with correct structure
            assert (project_dir / "root.txt").exists()
            assert (project_dir / "subdir" / "nested.txt").exists()
            assert (project_dir / "subdir" / "deep" / "deep.txt").exists()


@pytest.mark.integration
@pytest.mark.usefixtures("restore_cwd")
class TestSeedCommandScripts:
    """Tests for seed command script execution."""

    @pytest.fixture
    def script_setup(self):
        """Create a profile with scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir).resolve()

            # Create profiles directory
            profiles_dir = tmpdir / "profiles"
            profile_dir = profiles_dir / "with-scripts"
            profile_dir.mkdir(parents=True)

            # Create profile.toml
            (profile_dir / "profile.toml").write_text("""
[profile]
name = "with-scripts"
description = "Profile with scripts"

[scripts]
post_seed = ["scripts/01-setup.sh"]

[scripts.env]
CUSTOM_VAR = "custom-value"
""")

            # Create templates directory
            templates_dir = profile_dir / "templates"
            templates_dir.mkdir()
            (templates_dir / "README.txt").write_text("readme")

            # Create scripts directory
            scripts_dir = profile_dir / "scripts"
            scripts_dir.mkdir()

            # Create a script that writes to a marker file
            script_content = """#!/bin/bash
echo "Script executed" > script_executed.txt
echo "ADT_PROFILE=$ADT_PROFILE" >> script_executed.txt
echo "CUSTOM_VAR=$CUSTOM_VAR" >> script_executed.txt
"""
            script_path = scripts_dir / "01-setup.sh"
            script_path.write_text(script_content)
            script_path.chmod(0o755)

            # Create project directory
            project_dir = tmpdir / "project"
            project_dir.mkdir()

            config = ADTConfig(profiles_dir=profiles_dir, confirm_scripts=False)

            yield {
                "profile_dir": profile_dir,
                "profiles_dir": profiles_dir,
                "project_dir": project_dir,
                "config": config,
            }

    def test_seed_runs_scripts(self, script_setup):
        """Test that scripts are executed after seeding."""
        project_dir = script_setup["project_dir"]
        config = script_setup["config"]

        os.chdir(project_dir)

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(profile="with-scripts", yes=True)

        # Check that script ran (created marker file)
        marker_file = project_dir / "script_executed.txt"
        assert marker_file.exists()

        content = marker_file.read_text()
        assert "Script executed" in content
        assert "ADT_PROFILE=with-scripts" in content
        assert "CUSTOM_VAR=custom-value" in content

    def test_seed_scripts_with_confirmation_skip(self, script_setup, monkeypatch):
        """Test that scripts are skipped when user declines confirmation."""
        project_dir = script_setup["project_dir"]
        config = script_setup["config"]
        config.confirm_scripts = True  # Enable confirmation

        os.chdir(project_dir)

        # Simulate user declining
        monkeypatch.setattr("builtins.input", lambda _: "n")

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(profile="with-scripts")

        # Script should NOT have run
        marker_file = project_dir / "script_executed.txt"
        assert not marker_file.exists()

    def test_seed_scripts_auto_discovered(self):
        """Test that scripts in scripts/ directory are auto-discovered."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir).resolve()

            # Create profile with auto-discovered scripts
            profiles_dir = tmpdir / "profiles"
            profile_dir = profiles_dir / "auto-scripts"
            profile_dir.mkdir(parents=True)

            (profile_dir / "profile.toml").write_text("""
[profile]
name = "auto-scripts"
""")

            templates_dir = profile_dir / "templates"
            templates_dir.mkdir()
            (templates_dir / "file.txt").write_text("content")

            scripts_dir = profile_dir / "scripts"
            scripts_dir.mkdir()

            # Create multiple scripts (should be sorted alphabetically)
            for _i, name in enumerate(["02-second.sh", "01-first.sh"]):
                script = scripts_dir / name
                script.write_text(f"#!/bin/bash\necho '{name}' >> execution_order.txt\n")
                script.chmod(0o755)

            project_dir = tmpdir / "project"
            project_dir.mkdir()

            config = ADTConfig(profiles_dir=profiles_dir, confirm_scripts=False)

            os.chdir(project_dir)

            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = config

                cmd = create_seed_command()
                cmd.run(profile="auto-scripts", yes=True)

            # Check execution order (alphabetical)
            order_file = project_dir / "execution_order.txt"
            assert order_file.exists()
            lines = order_file.read_text().strip().split("\n")
            assert lines == ["01-first.sh", "02-second.sh"]

    def test_seed_scripts_with_condition(self):
        """Test that script conditions are evaluated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir).resolve()

            profiles_dir = tmpdir / "profiles"
            profile_dir = profiles_dir / "conditional"
            profile_dir.mkdir(parents=True)

            (profile_dir / "profile.toml").write_text("""
[profile]
name = "conditional"

[variables]
run_script = false

[scripts]
post_seed = [
    { script = "scripts/conditional.sh", condition = "run_script" }
]
""")

            templates_dir = profile_dir / "templates"
            templates_dir.mkdir()
            (templates_dir / "file.txt").write_text("content")

            scripts_dir = profile_dir / "scripts"
            scripts_dir.mkdir()
            script = scripts_dir / "conditional.sh"
            script.write_text("#!/bin/bash\necho 'ran' > conditional_ran.txt\n")
            script.chmod(0o755)

            project_dir = tmpdir / "project"
            project_dir.mkdir()

            config = ADTConfig(profiles_dir=profiles_dir, confirm_scripts=False)

            os.chdir(project_dir)

            with patch("abilian_devtools.commands.seed.load_config") as mock_config:
                mock_config.return_value = config

                cmd = create_seed_command()
                cmd.run(profile="conditional", yes=True)

            # Script should NOT have run (condition is false)
            assert not (project_dir / "conditional_ran.txt").exists()

    def test_seed_dry_run_skips_scripts(self, script_setup):
        """Test that dry run mode doesn't execute scripts."""
        project_dir = script_setup["project_dir"]
        config = script_setup["config"]

        os.chdir(project_dir)

        with patch("abilian_devtools.commands.seed.load_config") as mock_config:
            mock_config.return_value = config

            cmd = create_seed_command()
            cmd.run(profile="with-scripts", dry_run=True)

        # Script should NOT have run
        marker_file = project_dir / "script_executed.txt"
        assert not marker_file.exists()
