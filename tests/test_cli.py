from unittest import skip

import pytest
# from typer.testing import CliRunner

from abilian_devtools.main import main


@pytest.fixture()
def runner():
    return CliRunner()


@skip
def test_version(runner):
    result = runner.invoke(app, "--help")
    assert result.exit_code == 0
    assert "Abilian Dev Tools" in result.stdout


@skip
def test_bad_arg(runner):
    result = runner.invoke(app, "bad_arg")
    assert result.exit_code != 0
