import nox

PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13"]

nox.options.reuse_existing_virtualenvs = True

nox.options.sessions = [
    "lint",
    "pytest",
]


def install(session: nox.Session) -> None:
    """The project and its dev group, from the lockfile, in the session's
    virtualenv. With the uv backend, uv also fetches a missing interpreter."""
    session.run_install(
        "uv",
        "sync",
        "--locked",
        f"--python={session.virtualenv.location}",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )


@nox.session(python=PYTHON_VERSIONS, venv_backend="uv")
def lint(session: nox.Session):
    install(session)
    session.run("make", "lint", external=True)


@nox.session(python=PYTHON_VERSIONS, venv_backend="uv")
def pytest(session: nox.Session):
    install(session)
    session.run("pytest", "tests", "src")
