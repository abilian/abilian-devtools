# flake8: noqa

from abilian_devtools.commands.help import MakefileParser

MAKEFILE = """\
## Run (dev) server
run:
	honcho -f Procfile.dev start

## Run server under gunicorn
run-gunicorn:
	gunicorn -w1 'app.flask.main:create_app()'
"""


def test_make_parser():
    parser = MakefileParser()
    targets = parser.parse(MAKEFILE)
    assert targets == [
        ["run", "Run (dev) server"],
        ["run-gunicorn", "Run server under gunicorn"],
    ]
