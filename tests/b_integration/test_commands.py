"""The commands that wrap other tools: arguments, and exit status."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from abilian_devtools.cli import get_cli
from abilian_devtools.commands.clean import find_pycache_dirs
from abilian_devtools.shell import run

GIT = shutil.which("git") or "git"


def adt(*args: str) -> None:
    get_cli().run(["adt", *args])


class TestRun:
    def test_a_failure_exits_with_the_programs_status(self, capsys) -> None:
        with pytest.raises(SystemExit) as exit_info:
            run(["sh", "-c", "exit 3"])

        assert exit_info.value.code == 3
        assert "sh failed with exit status 3" in capsys.readouterr().out

    def test_with_warn_a_failure_is_returned(self) -> None:
        assert run(["sh", "-c", "exit 3"], warn=True) == 3

    def test_a_success_returns_zero(self) -> None:
        assert run(["true"]) == 0

    def test_arguments_are_not_split_again(self, tmp_path: Path) -> None:
        target = tmp_path / "with space.txt"

        run(["touch", str(target)])

        assert [p.name for p in tmp_path.iterdir()] == ["with space.txt"]


class TestCheck:
    def test_a_lint_failure_fails_the_command(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text("x = 1 +\n")

        with pytest.raises(SystemExit) as exit_info:
            adt("check", str(tmp_path / "bad.py"))

        assert exit_info.value.code != 0


class TestTargets:
    def test_test_takes_several_paths(self, tmp_path, monkeypatch, capsys) -> None:
        """Each path is checked whole, not letter by letter."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "here").mkdir()

        with pytest.raises(SystemExit) as exit_info:
            adt("test", "here", "missing")

        assert exit_info.value.code == 1
        assert capsys.readouterr().out.strip().endswith("missing does not exist")


class TestClean:
    def test_finds_pycache_outside_hidden_directories(self, tmp_path: Path) -> None:
        for directory in ["src/pkg/__pycache__", "__pycache__", ".venv/__pycache__"]:
            (tmp_path / directory).mkdir(parents=True)

        found = find_pycache_dirs(tmp_path)

        assert sorted(p.relative_to(tmp_path) for p in found) == [
            Path("__pycache__"),
            Path("src/pkg/__pycache__"),
        ]


class TestBumpVersion:
    @pytest.fixture
    def repo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """A git repository with a committed pyproject.toml, and no git
        configuration from the developer's machine."""
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        for role in ("AUTHOR", "COMMITTER"):
            monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
            monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.com")
        repo = tmp_path / "repo"
        repo.mkdir()
        monkeypatch.chdir(repo)
        (repo / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
        (repo / "other.txt").write_text("other\n")
        for command in (["init", "-q"], ["add", "."], ["commit", "-qm", "init"]):
            subprocess.run([GIT, *command], check=True)
        return repo

    def test_a_staged_change_stops_the_bump(self, repo: Path, capsys) -> None:
        (repo / "other.txt").write_text("staged\n")
        subprocess.run([GIT, "add", "other.txt"], check=True)

        with pytest.raises(SystemExit) as exit_info:
            adt("bump-version")

        assert exit_info.value.code == 1
        assert "uncommitted changes" in capsys.readouterr().out
        assert 'version = "1.2.3"' in (repo / "pyproject.toml").read_text()
