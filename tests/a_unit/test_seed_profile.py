# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Unit tests for seed profile module."""

import tempfile
from pathlib import Path

import pytest

from abilian_devtools.seed.config import ADTConfig
from abilian_devtools.seed.profile import (
    FileMapping,
    Profile,
    ProfileError,
    ScriptConfig,
    load_profile,
    resolve_profile_chain,
    validate_profile,
)


@pytest.mark.unit
class TestProfile:
    """Tests for Profile dataclass."""

    def test_default_values(self):
        """Test that Profile has sensible defaults."""
        profile = Profile(name="test")
        assert profile.name == "test"
        assert profile.description == ""
        assert profile.version == "1.0.0"
        assert profile.extends == []
        assert profile.variables == {}

    def test_templates_dir_property(self):
        """Test templates_dir property returns correct path."""
        profile = Profile(name="test", path=Path("/some/path"))
        assert profile.templates_dir == Path("/some/path/templates")

    def test_scripts_dir_property(self):
        """Test scripts_dir property returns correct path."""
        profile = Profile(name="test", path=Path("/some/path"))
        assert profile.scripts_dir == Path("/some/path/scripts")

    def test_get_template_files_with_explicit_mappings(self):
        """Test get_template_files returns explicit mappings if defined."""
        mappings = [
            FileMapping(source=Path("/a"), dest="a.txt"),
            FileMapping(source=Path("/b"), dest="b.txt"),
        ]
        profile = Profile(name="test", file_mappings=mappings)
        assert profile.get_template_files() == mappings

    def test_get_template_files_auto_discovery(self):
        """Test get_template_files auto-discovers templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()

            # Create some template files
            (templates_dir / "readme.txt").write_text("readme content")
            (templates_dir / "config.json.j2").write_text('{"key": "value"}')
            subdir = templates_dir / "subdir"
            subdir.mkdir()
            (subdir / "nested.txt").write_text("nested")

            profile = Profile(name="test", path=profile_path)
            mappings = profile.get_template_files()

            # Should find all 3 files
            assert len(mappings) == 3

            # Check destinations
            dests = {m.dest for m in mappings}
            assert "readme.txt" in dests
            assert "config.json" in dests  # .j2 stripped
            assert "subdir/nested.txt" in dests

            # Check is_template flag
            template_mapping = next(m for m in mappings if m.dest == "config.json")
            assert template_mapping.is_template is True

            non_template = next(m for m in mappings if m.dest == "readme.txt")
            assert non_template.is_template is False

    def test_get_template_files_skips_pycache(self):
        """Test get_template_files skips __pycache__ directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()

            (templates_dir / "file.txt").write_text("content")
            pycache = templates_dir / "__pycache__"
            pycache.mkdir()
            (pycache / "cached.pyc").write_text("cache")

            profile = Profile(name="test", path=profile_path)
            mappings = profile.get_template_files()

            assert len(mappings) == 1
            assert mappings[0].dest == "file.txt"

    def test_get_template_files_empty_templates_dir(self):
        """Test get_template_files returns empty list for empty templates dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()

            profile = Profile(name="test", path=profile_path)
            mappings = profile.get_template_files()
            assert mappings == []

    def test_get_template_files_no_templates_dir(self):
        """Test get_template_files returns empty list if templates dir doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile = Profile(name="test", path=profile_path)
            mappings = profile.get_template_files()
            assert mappings == []

    def test_get_scripts_with_explicit_scripts(self):
        """Test get_scripts returns explicit scripts if defined."""
        scripts = [
            ScriptConfig(path=Path("/script1.sh")),
            ScriptConfig(path=Path("/script2.sh")),
        ]
        profile = Profile(name="test", scripts=scripts)
        assert profile.get_scripts() == scripts

    def test_get_scripts_auto_discovery(self):
        """Test get_scripts auto-discovers scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            scripts_dir = profile_path / "scripts"
            scripts_dir.mkdir()

            # Create some script files
            (scripts_dir / "01-setup.sh").write_text("#!/bin/bash\necho setup")
            (scripts_dir / "02-install.sh").write_text("#!/bin/bash\necho install")
            (scripts_dir / ".hidden").write_text("hidden")  # Should be ignored

            profile = Profile(name="test", path=profile_path)
            scripts = profile.get_scripts()

            # Should find 2 scripts (excluding hidden)
            assert len(scripts) == 2

            # Should be sorted alphabetically
            assert scripts[0].path.name == "01-setup.sh"
            assert scripts[1].path.name == "02-install.sh"

    def test_get_scripts_no_scripts_dir(self):
        """Test get_scripts returns empty list if scripts dir doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = Profile(name="test", path=Path(tmpdir))
            assert profile.get_scripts() == []


@pytest.mark.unit
class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_profile_from_path(self):
        """Test loading a profile by path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "my-profile"
description = "A test profile"
version = "2.0.0"
""")

            profile = load_profile(str(profile_path))
            assert profile.name == "my-profile"
            assert profile.description == "A test profile"
            assert profile.version == "2.0.0"
            assert profile.path == profile_path

    def test_load_profile_minimal(self):
        """Test loading a profile without profile.toml uses directory name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "my-test-profile"
            profile_path.mkdir()

            profile = load_profile(str(profile_path))
            assert profile.name == "my-test-profile"
            assert profile.path == profile_path

    def test_load_profile_with_extends(self):
        """Test loading a profile with extends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "child"
extends = ["base", "common"]
""")

            profile = load_profile(str(profile_path))
            assert profile.extends == ["base", "common"]

    def test_load_profile_with_extends_string(self):
        """Test loading a profile with extends as single string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "child"
extends = "base"
""")

            profile = load_profile(str(profile_path))
            assert profile.extends == ["base"]

    def test_load_profile_with_variables(self):
        """Test loading a profile with variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "with-vars"

[variables]
author = "Test Author"
use_docker = true
port = 8080
""")

            profile = load_profile(str(profile_path))
            assert profile.variables["author"] == "Test Author"
            assert profile.variables["use_docker"] is True
            assert profile.variables["port"] == 8080

    def test_load_profile_with_file_mappings(self):
        """Test loading a profile with explicit file mappings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "config.j2").write_text("{{ value }}")

            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "with-files"

[files]
"config.j2" = "config.json"
""")

            profile = load_profile(str(profile_path))
            assert len(profile.file_mappings) == 1
            assert profile.file_mappings[0].dest == "config.json"
            assert profile.file_mappings[0].is_template is True

    def test_load_profile_with_conditional_files(self):
        """Test loading a profile with conditional file mappings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "docker.yml").write_text("version: 3")

            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "with-condition"

[files]
"docker.yml" = { dest = "docker-compose.yml", condition = "use_docker" }
""")

            profile = load_profile(str(profile_path))
            assert len(profile.file_mappings) == 1
            assert profile.file_mappings[0].dest == "docker-compose.yml"
            assert profile.file_mappings[0].condition == "use_docker"

    def test_load_profile_with_scripts(self):
        """Test loading a profile with scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            scripts_dir = profile_path / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "setup.sh").write_text("#!/bin/bash")

            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "with-scripts"

[scripts]
post_seed = ["scripts/setup.sh"]
""")

            profile = load_profile(str(profile_path))
            assert len(profile.scripts) == 1
            assert profile.scripts[0].path.name == "setup.sh"

    def test_load_profile_with_script_env(self):
        """Test loading a profile with script environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("""
[profile]
name = "with-env"

[scripts]
post_seed = []

[scripts.env]
MY_VAR = "my-value"
""")

            profile = load_profile(str(profile_path))
            assert profile.script_env["MY_VAR"] == "my-value"

    def test_load_profile_not_found(self):
        """Test load_profile raises error for non-existent profile."""
        with pytest.raises(ProfileError, match="Profile not found"):
            load_profile("nonexistent-profile-xyz")

    def test_load_profile_invalid_toml(self):
        """Test load_profile raises error for invalid TOML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            profile_toml = profile_path / "profile.toml"
            profile_toml.write_text("invalid [ toml ]]]]")

            with pytest.raises(ProfileError, match="Failed to parse"):
                load_profile(str(profile_path))

    def test_load_profile_by_name(self):
        """Test loading a profile by name from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create profiles directory
            profiles_dir = Path(tmpdir) / "profiles"
            profile_path = profiles_dir / "my-profile"
            profile_path.mkdir(parents=True)
            (profile_path / "profile.toml").write_text("""
[profile]
name = "my-profile"
description = "Loaded by name"
""")

            # Create config with profiles_dir
            config = ADTConfig(profiles_dir=profiles_dir)

            profile = load_profile("my-profile", config)
            assert profile.name == "my-profile"
            assert profile.description == "Loaded by name"


@pytest.mark.unit
class TestResolveProfileChain:
    """Tests for resolve_profile_chain function."""

    def test_resolve_single_profile(self):
        """Test resolving a single profile without inheritance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profile_path = profiles_dir / "simple"
            profile_path.mkdir(parents=True)
            (profile_path / "profile.toml").write_text("""
[profile]
name = "simple"
""")

            config = ADTConfig(profiles_dir=profiles_dir)
            chain = resolve_profile_chain(["simple"], config)

            assert len(chain) == 1
            assert chain[0].name == "simple"

    def test_resolve_multiple_profiles(self):
        """Test resolving multiple profiles in order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()

            for name in ["a", "b", "c"]:
                p = profiles_dir / name
                p.mkdir()
                (p / "profile.toml").write_text(f"""
[profile]
name = "{name}"
""")

            config = ADTConfig(profiles_dir=profiles_dir)

            chain = resolve_profile_chain(["a", "b", "c"], config)
            assert len(chain) == 3
            assert [p.name for p in chain] == ["a", "b", "c"]

    def test_resolve_with_inheritance(self):
        """Test resolving profiles with inheritance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()

            # Base profile
            base = profiles_dir / "base"
            base.mkdir()
            (base / "profile.toml").write_text("""
[profile]
name = "base"
""")

            # Child profile
            child = profiles_dir / "child"
            child.mkdir()
            (child / "profile.toml").write_text("""
[profile]
name = "child"
extends = ["base"]
""")

            config = ADTConfig(profiles_dir=profiles_dir)

            chain = resolve_profile_chain(["child"], config)
            assert len(chain) == 2
            # Base should come first (dependency order)
            assert chain[0].name == "base"
            assert chain[1].name == "child"

    def test_resolve_deep_inheritance(self):
        """Test resolving profiles with deep inheritance chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()

            # Create grandparent -> parent -> child chain
            grandparent = profiles_dir / "grandparent"
            grandparent.mkdir()
            (grandparent / "profile.toml").write_text("""
[profile]
name = "grandparent"
""")

            parent = profiles_dir / "parent"
            parent.mkdir()
            (parent / "profile.toml").write_text("""
[profile]
name = "parent"
extends = ["grandparent"]
""")

            child = profiles_dir / "child"
            child.mkdir()
            (child / "profile.toml").write_text("""
[profile]
name = "child"
extends = ["parent"]
""")

            config = ADTConfig(profiles_dir=profiles_dir)

            chain = resolve_profile_chain(["child"], config)
            assert len(chain) == 3
            assert [p.name for p in chain] == ["grandparent", "parent", "child"]

    def test_resolve_duplicate_profiles_only_once(self):
        """Test that duplicate profiles are only included once."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles_dir = Path(tmpdir) / "profiles"
            profiles_dir.mkdir()

            # Common base
            base = profiles_dir / "base"
            base.mkdir()
            (base / "profile.toml").write_text("""
[profile]
name = "base"
""")

            # Two profiles both extending base
            for name in ["a", "b"]:
                p = profiles_dir / name
                p.mkdir()
                (p / "profile.toml").write_text(f"""
[profile]
name = "{name}"
extends = ["base"]
""")

            config = ADTConfig(profiles_dir=profiles_dir)

            # Request both a and b, which both extend base
            chain = resolve_profile_chain(["a", "b"], config)

            # Base should only appear once
            names = [p.name for p in chain]
            assert names.count("base") == 1
            assert len(chain) == 3


@pytest.mark.unit
class TestValidateProfile:
    """Tests for validate_profile function."""

    def test_validate_valid_profile(self):
        """Test validation passes for a valid profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()
            (templates_dir / "file.txt").write_text("content")

            profile = Profile(name="valid", path=profile_path)
            errors = validate_profile(profile)
            assert errors == []

    def test_validate_missing_name(self):
        """Test validation fails for missing name."""
        profile = Profile(name="", path=Path("/tmp"))
        errors = validate_profile(profile)
        assert any("name" in e.lower() for e in errors)

    def test_validate_missing_path(self):
        """Test validation fails for non-existent path."""
        profile = Profile(name="test", path=Path("/nonexistent/path/xyz"))
        errors = validate_profile(profile)
        assert any("path" in e.lower() for e in errors)

    def test_validate_empty_templates_dir(self):
        """Test validation warns about empty templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            templates_dir = profile_path / "templates"
            templates_dir.mkdir()
            # Empty templates dir

            profile = Profile(name="test", path=profile_path)
            errors = validate_profile(profile)
            assert any("empty" in e.lower() for e in errors)

    def test_validate_missing_script(self):
        """Test validation fails for missing scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = Profile(
                name="test",
                path=Path(tmpdir),
                scripts=[ScriptConfig(path=Path("/nonexistent/script.sh"))],
            )
            errors = validate_profile(profile)
            assert any("script" in e.lower() for e in errors)


@pytest.mark.unit
class TestFileMapping:
    """Tests for FileMapping dataclass."""

    def test_file_mapping_defaults(self):
        """Test FileMapping default values."""
        mapping = FileMapping(source=Path("/a"), dest="b")
        assert mapping.condition is None
        assert mapping.is_template is False

    def test_file_mapping_with_condition(self):
        """Test FileMapping with condition."""
        mapping = FileMapping(
            source=Path("/a"),
            dest="b",
            condition="use_feature",
            is_template=True,
        )
        assert mapping.condition == "use_feature"
        assert mapping.is_template is True


@pytest.mark.unit
class TestScriptConfig:
    """Tests for ScriptConfig dataclass."""

    def test_script_config_defaults(self):
        """Test ScriptConfig default values."""
        script = ScriptConfig(path=Path("/script.sh"))
        assert script.condition is None

    def test_script_config_with_condition(self):
        """Test ScriptConfig with condition."""
        script = ScriptConfig(path=Path("/script.sh"), condition="has_docker")
        assert script.condition == "has_docker"
