# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Integration tests for the seed command.

Each test runs `adt seed` through the real command-line parser, in a project
directory of its own, with a global configuration file the test writes (the
root conftest puts it in the test's temporary directory).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from abilian_devtools.cli import get_cli

if TYPE_CHECKING:
    from pathlib import Path

BUILTIN_FILES = {".envrc", ".gitignore", ".pre-commit-config.yaml", "Makefile"}
BUILTIN_FILES |= {"ruff.toml"}


def adt(*args: str) -> None:
    get_cli().run(["adt", *args])


def adt_fails(*args: str) -> None:
    """Run adt, which must exit with status 1."""
    with pytest.raises(SystemExit) as exit_info:
        adt(*args)
    assert exit_info.value.code == 1


def files_in(directory: Path) -> set[str]:
    return {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()}


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty project directory, the current directory."""
    path = tmp_path / "project"
    path.mkdir()
    monkeypatch.chdir(path)
    return path


@pytest.fixture
def profiles_dir(tmp_path: Path, global_config_file: Path) -> Path:
    """A directory of profiles, named in the global config. Scripts run
    without confirmation, unless a test writes another config."""
    path = tmp_path / "profiles"
    path.mkdir()
    write_config(global_config_file, path, confirm_scripts=False)
    return path


def write_config(config_file: Path, profiles_dir: Path, *, confirm_scripts: bool):
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        f'[seed]\nprofiles_dir = "{profiles_dir}"\n\n'
        f"[settings]\nconfirm_scripts = {str(confirm_scripts).lower()}\n"
    )


def make_profile(
    profiles_dir: Path,
    name: str,
    toml: str = "",
    templates: dict[str, str] | None = None,
    scripts: dict[str, str] | None = None,
) -> Path:
    """A profile: its profile.toml, templates and scripts."""
    path = profiles_dir / name
    path.mkdir()
    (path / "profile.toml").write_text(f'[profile]\nname = "{name}"\n{toml}')
    for rel_path, content in (templates or {}).items():
        dest = path / "templates" / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    for rel_path, content in (scripts or {}).items():
        dest = path / "scripts" / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        dest.chmod(0o755)
    return path


@pytest.mark.integration
class TestSeedBuiltin:
    """Without a profile: the files shipped with abilian-devtools."""

    def test_creates_the_builtin_files(self, project: Path) -> None:
        adt("seed", "-y")

        assert files_in(project) == BUILTIN_FILES

    def test_dry_run_creates_nothing(self, project: Path) -> None:
        adt("seed", "-n")

        assert files_in(project) == set()

    def test_existing_files_are_kept(self, project: Path, capsys) -> None:
        (project / ".gitignore").write_text("existing content")

        adt("seed", "-y")

        assert (project / ".gitignore").read_text() == "existing content"
        assert files_in(project) == BUILTIN_FILES
        assert "skip .gitignore (exists)" in capsys.readouterr().out


@pytest.mark.integration
class TestSeedWithProfile:
    @pytest.fixture(autouse=True)
    def profile(self, profiles_dir: Path) -> Path:
        return make_profile(
            profiles_dir,
            "test-profile",
            'description = "A test profile"\n\n'
            '[variables]\nauthor = "Test Author"\nyear = 2025\n',
            templates={
                "README.txt": "Plain readme",
                "LICENSE.j2": "Copyright {{ year }} {{ author }}\n",
            },
        )

    def test_creates_and_renders_the_files(self, project: Path) -> None:
        adt("seed", "-p", "test-profile", "-y")

        assert files_in(project) == {"README.txt", "LICENSE"}
        assert (project / "README.txt").read_text() == "Plain readme"
        assert (project / "LICENSE").read_text() == "Copyright 2025 Test Author\n"

    def test_dry_run_creates_nothing(self, project: Path, capsys) -> None:
        adt("seed", "-p", "test-profile", "-n", "-y")

        assert files_in(project) == set()
        assert "would create README.txt" in capsys.readouterr().out

    def test_overwrite_replaces_existing_files(self, project: Path) -> None:
        (project / "README.txt").write_text("old content")

        adt("seed", "-p", "test-profile", "-o", "-y")

        assert (project / "README.txt").read_text() == "Plain readme"

    def test_a_cli_variable_wins(self, project: Path) -> None:
        adt("seed", "-p", "test-profile", "-y", "-v", "author=Someone Else")

        assert (project / "LICENSE").read_text() == "Copyright 2025 Someone Else\n"

    def test_a_variable_without_a_value_is_an_error(self, project, capsys) -> None:
        adt_fails("seed", "-p", "test-profile", "-y", "-v", "author")

        assert "'author' has no value" in capsys.readouterr().err
        assert files_in(project) == set()

    def test_an_unknown_profile_is_an_error(self, project: Path, capsys) -> None:
        """Not a reason to seed the built-in files instead."""
        adt_fails("seed", "-p", "test-profil", "-y")

        assert "'test-profil' not found" in capsys.readouterr().err
        assert files_in(project) == set()

    def test_lists_the_profiles(self, project: Path, capsys) -> None:
        adt("seed", "--list")

        assert "test-profile: A test profile" in capsys.readouterr().out

    def test_shows_a_profiles_info(self, project: Path, capsys) -> None:
        adt("seed", "--info", "test-profile")

        out = capsys.readouterr().out
        assert "Profile: test-profile" in out
        assert "A test profile" in out
        assert "author = Test Author" in out

    def test_info_on_an_unknown_profile_is_an_error(self, project, capsys) -> None:
        adt_fails("seed", "--info", "nope")

        assert "Profile not found: nope" in capsys.readouterr().err


@pytest.mark.integration
class TestSeedFailures:
    """A file or script that fails: the others are seeded, and seed exits 1."""

    def test_a_template_error(self, project: Path, profiles_dir: Path) -> None:
        make_profile(
            profiles_dir,
            "broken",
            templates={"bad.txt.j2": "{{ unclosed", "good.txt": "fine"},
        )

        adt_fails("seed", "-p", "broken", "-y")

        assert files_in(project) == {"good.txt"}

    def test_a_condition_that_cant_be_evaluated(self, project, profiles_dir) -> None:
        make_profile(
            profiles_dir,
            "typo",
            "[variables]\nuse_docker = true\n\n"
            '[files]\n"Dockerfile" = { dest = "Dockerfile", condition = "use_dockr" }\n'
            '"good.txt" = "good.txt"\n',
            templates={"Dockerfile": "FROM python", "good.txt": "fine"},
        )

        adt_fails("seed", "-p", "typo", "-y")

        assert files_in(project) == {"good.txt"}

    def test_a_failing_script(self, project: Path, profiles_dir: Path) -> None:
        make_profile(
            profiles_dir,
            "failing",
            templates={"file.txt": "content"},
            scripts={"01-fail.sh": "#!/bin/sh\nexit 3\n"},
        )

        adt_fails("seed", "-p", "failing", "-y")

        assert files_in(project) == {"file.txt"}


@pytest.mark.integration
class TestSeedProfileFeatures:
    def test_inherited_files_are_seeded(self, project, profiles_dir) -> None:
        make_profile(profiles_dir, "base", templates={"base.txt": "from base"})
        make_profile(
            profiles_dir,
            "child",
            'extends = ["base"]\n',
            templates={"child.txt": "from child"},
        )

        adt("seed", "-p", "child", "-y")

        assert files_in(project) == {"base.txt", "child.txt"}

    def test_resolves_the_variables(self, project, profiles_dir) -> None:
        make_profile(
            profiles_dir,
            "vars",
            '[variables]\nprofile_var = "from_profile"\n',
            templates={
                "vars.txt.j2": "Project: {{ project_name }}\n"
                "Version: {{ project_version }}\n"
                "Year: {{ current_year }}\n"
                "Profile Var: {{ profile_var }}\n"
                "Has Src: {{ has_src_layout }}\n"
            },
        )
        (project / "pyproject.toml").write_text(
            '[project]\nname = "my-awesome-project"\nversion = "2.5.0"\n'
        )
        (project / "src").mkdir()
        year = datetime.now().year  # seed's current_year: the local date

        adt("seed", "-p", "vars", "-y")

        assert (project / "vars.txt").read_text() == (
            "Project: my-awesome-project\n"
            "Version: 2.5.0\n"
            f"Year: {year}\n"
            "Profile Var: from_profile\n"
            "Has Src: True\n"
        )

    def test_creates_nested_directories(self, project, profiles_dir) -> None:
        make_profile(
            profiles_dir,
            "nested",
            templates={
                "root.txt": "root file",
                "subdir/nested.txt": "nested file",
                "subdir/deep/deep.txt": "deep file",
            },
        )

        adt("seed", "-p", "nested", "-y")

        assert files_in(project) == {
            "root.txt",
            "subdir/nested.txt",
            "subdir/deep/deep.txt",
        }


@pytest.mark.integration
class TestSeedScripts:
    SCRIPT = (
        "#!/bin/sh\n"
        'echo "ADT_PROFILE=$ADT_PROFILE" > script_ran.txt\n'
        'echo "CUSTOM_VAR=$CUSTOM_VAR" >> script_ran.txt\n'
    )

    @pytest.fixture
    def with_scripts(self, profiles_dir: Path) -> Path:
        return make_profile(
            profiles_dir,
            "with-scripts",
            '[scripts]\npost_seed = ["scripts/01-setup.sh"]\n\n'
            '[scripts.env]\nCUSTOM_VAR = "custom-value"\n',
            templates={"README.txt": "readme"},
            scripts={"01-setup.sh": self.SCRIPT},
        )

    @pytest.mark.usefixtures("with_scripts")
    def test_runs_the_scripts(self, project: Path) -> None:
        adt("seed", "-p", "with-scripts", "-y")

        assert (project / "script_ran.txt").read_text() == (
            "ADT_PROFILE=with-scripts\nCUSTOM_VAR=custom-value\n"
        )

    @pytest.mark.usefixtures("with_scripts")
    def test_scripts_declined_dont_run(
        self, project, profiles_dir, global_config_file, monkeypatch
    ) -> None:
        write_config(global_config_file, profiles_dir, confirm_scripts=True)
        answers = iter(["y", "n"])  # create README.txt, run the scripts
        monkeypatch.setattr("builtins.input", lambda _: next(answers))

        adt("seed", "-p", "with-scripts")

        assert files_in(project) == {"README.txt"}

    @pytest.mark.usefixtures("with_scripts")
    def test_dry_run_runs_no_script(self, project: Path) -> None:
        adt("seed", "-p", "with-scripts", "-n")

        assert files_in(project) == set()

    def test_scripts_are_discovered_in_order(self, project, profiles_dir) -> None:
        make_profile(
            profiles_dir,
            "auto-scripts",
            templates={"file.txt": "content"},
            scripts={
                name: f"#!/bin/sh\necho '{name}' >> order.txt\n"
                for name in ["02-second.sh", "01-first.sh"]
            },
        )

        adt("seed", "-p", "auto-scripts", "-y")

        assert (project / "order.txt").read_text() == "01-first.sh\n02-second.sh\n"

    def test_a_scripts_condition_is_honoured(self, project, profiles_dir) -> None:
        make_profile(
            profiles_dir,
            "conditional",
            "[variables]\nrun_script = false\n\n"
            "[scripts]\npost_seed = [\n"
            '  { script = "scripts/conditional.sh", condition = "run_script" }\n]\n',
            templates={"file.txt": "content"},
            scripts={"conditional.sh": "#!/bin/sh\necho ran > ran.txt\n"},
        )

        adt("seed", "-p", "conditional", "-y")

        assert files_in(project) == {"file.txt"}


@pytest.mark.integration
class TestSeedInteractive:
    @pytest.fixture(autouse=True)
    def profile(self, profiles_dir: Path) -> Path:
        return make_profile(
            profiles_dir,
            "interactive",
            templates={f"file{i}.txt": f"content{i}" for i in (1, 2, 3)},
        )

    def test_prompts_for_each_file(self, project: Path, monkeypatch) -> None:
        answers = iter(["n", "y", "n"])
        monkeypatch.setattr("builtins.input", lambda _: next(answers))

        adt("seed", "-p", "interactive")

        assert files_in(project) == {"file2.txt"}

    def test_all_accepts_the_remaining_files(self, project, monkeypatch) -> None:
        answers = iter(["n", "a"])
        monkeypatch.setattr("builtins.input", lambda _: next(answers))

        adt("seed", "-p", "interactive")

        assert files_in(project) == {"file2.txt", "file3.txt"}
