"""A pytest plugin: the tests read no setting from the developer's machine.

A project names its pydantic-settings class in its pytest configuration:

    [tool.pytest.ini_options]
    settings_class = "app.config:Settings"

Before any `conftest.py` is imported, the plugin removes from the process's
environment every variable that class reads, and turns off its `.env` file.
Each test then sets what it needs. Without a variable exported by direnv or
a secret in `.env`, a test can't pass on the developer's machine and fail on
a build machine for want of them.

Without the option, the plugin does nothing.
"""

from __future__ import annotations

import importlib
import os
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

OPTION = "settings_class"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        OPTION,
        "A pydantic-settings class, as module:Class: the tests ignore the "
        "environment variables it reads and its .env file.",
        default="",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: pytest.Config) -> None:
    """Before the conftest files: what they import must see no setting of the
    machine either."""
    name = early_config.getini(OPTION)
    if name:
        isolate(load(name))


def load(name: str) -> Any:
    """The class named "module:Class"."""
    module, _, attribute = name.partition(":")
    if not (module and attribute):
        msg = f"{OPTION} = {name!r}: write it as module:Class (app.config:Settings)"
        raise pytest.UsageError(msg)
    try:
        return getattr(importlib.import_module(module), attribute)
    except (ImportError, AttributeError) as e:
        msg = f"{OPTION} = {name!r}: {e}"
        raise pytest.UsageError(msg) from e


def isolate(settings_class: Any) -> list[str]:
    """Remove the environment variables the class reads, and turn off its .env
    file.

    The variables removed, by name.
    """
    names = set(environment_names(settings_class))
    case_sensitive = settings_class.model_config.get("case_sensitive", False)
    removed = [
        key
        for key in list(os.environ)
        if (key if case_sensitive else key.upper()) in names
    ]
    for key in removed:
        del os.environ[key]
    settings_class.model_config["env_file"] = None
    return sorted(removed)


def environment_names(settings_class: Any) -> Iterator[str]:
    """The names of the environment variables a pydantic-settings class
    reads: each field's alias, or its alias choices, or the class's prefix
    and the field's name. Upper case, unless the class is case-sensitive."""
    config = settings_class.model_config
    case_sensitive = config.get("case_sensitive", False)
    prefix = config.get("env_prefix", "")
    for field_name, field in settings_class.model_fields.items():
        alias = field.validation_alias or field.alias
        if isinstance(alias, str):
            names = [alias]
        elif choices := getattr(alias, "choices", None):  # AliasChoices
            names = [choice for choice in choices if isinstance(choice, str)]
        else:
            names = [prefix + field_name]
        for name in names:
            yield name if case_sensitive else name.upper()
