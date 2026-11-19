"""The pytest plugin: a project's tests read no setting of the machine.

Each test runs pytest on a small project, in a subprocess, so that the
plugin loads as it does elsewhere: from its entry point."""

from __future__ import annotations

import textwrap

import pytest

pytest_plugins = ["pytester"]

SETTINGS = """
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env")

    debug: bool = Field(default=False, alias="DEBUG")
    secret_key: str = Field(default="placeholder", alias="SECRET_KEY")
    region: str = "eu"  # APP_REGION
    token: str = Field(default="", validation_alias=AliasChoices("TOKEN", "API_TOKEN"))
"""

# At import, as a project's conftest may: the plugin must have run before.
CONFTEST = """
import os

SEEN_AT_IMPORT = {name: os.environ.get(name) for name in ("DEBUG", "SECRET_KEY")}
"""

TESTS = """
import os

from conftest import SEEN_AT_IMPORT
from settings import Settings


def test_the_machines_settings_are_gone():
    assert SEEN_AT_IMPORT == {"DEBUG": None, "SECRET_KEY": None}
    for name in ("DEBUG", "SECRET_KEY", "APP_REGION", "API_TOKEN", "app_region"):
        assert name not in os.environ, name
    assert os.environ["UNRELATED"] == "kept"


def test_the_dotenv_file_is_ignored():
    assert Settings().secret_key == "placeholder"
"""


@pytest.fixture
def project(pytester: pytest.Pytester, monkeypatch: pytest.MonkeyPatch):
    """A project with a settings class, and a machine that sets them all,
    in its environment and in .env."""
    pytester.makepyfile(settings=SETTINGS, conftest=CONFTEST, test_project=TESTS)
    (pytester.path / ".env").write_text("SECRET_KEY=from-the-dotenv-file\n")
    monkeypatch.setenv("PYTHONPATH", str(pytester.path))
    for name, value in {
        "DEBUG": "true",
        "SECRET_KEY": "from-the-shell",
        "APP_REGION": "us",
        "app_region": "us",  # case-insensitive, as pydantic-settings reads it
        "API_TOKEN": "t0k3n",
        "UNRELATED": "kept",
    }.items():
        monkeypatch.setenv(name, value)
    return pytester


def configure(pytester: pytest.Pytester, option: str) -> None:
    pytester.makepyprojecttoml(
        textwrap.dedent(f"""
        [tool.pytest.ini_options]
        {option}
        """)
    )


def test_the_settings_of_the_machine_are_ignored(project: pytest.Pytester) -> None:
    configure(project, 'settings_class = "settings:Settings"')

    result = project.runpytest_subprocess("-p", "no:randomly", "-p", "no:random_order")

    result.assert_outcomes(passed=2)


def test_without_the_option_nothing_changes(project: pytest.Pytester) -> None:
    configure(project, "")

    result = project.runpytest_subprocess("-p", "no:randomly", "-p", "no:random_order")

    result.assert_outcomes(failed=2)  # the machine's settings are all there


def test_a_settings_class_that_cant_be_found_is_an_error(
    project: pytest.Pytester,
) -> None:
    configure(project, 'settings_class = "settings:Nope"')

    result = project.runpytest_subprocess()

    assert result.ret == pytest.ExitCode.USAGE_ERROR
    result.stderr.fnmatch_lines(["*settings_class = 'settings:Nope'*"])
