# SPDX-FileCopyrightText: 2025 Abilian SAS <https://abilian.com/>
#
# SPDX-License-Identifier: MIT

"""Unit tests for MakefileParser."""

import pytest

from abilian_devtools.commands.help import MakefileParser

MAKEFILE = """\
## Run (dev) server
run:
	honcho -f Procfile.dev start

## Run server under gunicorn
run-gunicorn:
	gunicorn -w1 'app.flask.main:create_app()'
"""


@pytest.mark.unit
class TestMakefileParser:
    """Tests for MakefileParser class."""

    def test_parse_extracts_targets_with_comments(self):
        # Arrange
        parser = MakefileParser()

        # Act
        targets = parser.parse(MAKEFILE)

        # Assert
        assert targets == [
            ["run", "Run (dev) server"],
            ["run-gunicorn", "Run server under gunicorn"],
        ]
