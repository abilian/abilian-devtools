"""A pytest plugin: the tests read no setting from the developer's machine.

A project names its pydantic-settings class in its pytest configuration:

    [tool.pytest.ini_options]
    settings_class = "app.config:Settings"

Before any `conftest.py` is imported, the plugin removes from the process's
environment every variable that class reads, and turns off its `.env` file
and its secrets directory. An instance the class's module (or a module it
imports) created at import, such as `settings = Settings()`, is created
again, from the cleaned environment. Each test then sets what it needs.
Without a variable exported by direnv or a secret in `.env`, a test can't
pass on the developer's machine and fail on a build machine for want of them.

Without the option, the plugin does nothing.
"""

from __future__ import annotations

import importlib
import os
import sys
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
    if not name:
        return
    already_loaded = set(sys.modules)
    settings_class = load(name)
    isolate(settings_class)
    instances = instances_created_at_import(settings_class, already_loaded)
    for where, instance in instances.items():
        recreate(instance, f"{OPTION} = {name!r}: {where}")


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


def isolate(settings_class: Any) -> None:
    """Remove the environment variables the class reads, and turn off its .env
    file and its secrets directory."""
    config = settings_class.model_config
    case_sensitive = config.get("case_sensitive", False)
    names = set(environment_names(settings_class))
    delimiter = config.get("env_nested_delimiter") or ""
    if not case_sensitive:
        delimiter = delimiter.upper()
    # A nested field's variables: APP_DB__HOST for the field db.
    prefixes = tuple(name + delimiter for name in names) if delimiter else ()

    for key in list(os.environ):
        normalized = key if case_sensitive else key.upper()
        if normalized in names or (prefixes and normalized.startswith(prefixes)):
            del os.environ[key]
    config["env_file"] = None
    config["secrets_dir"] = None


def environment_names(settings_class: Any) -> Iterator[str]:
    """The names of the environment variables a pydantic-settings class
    reads: each field's alias, or its alias choices, or the class's prefix
    and the field's name. Upper case, unless the class is case-sensitive."""
    config = settings_class.model_config
    case_sensitive = config.get("case_sensitive", False)
    prefix = config.get("env_prefix", "")
    for field_name, field in settings_class.model_fields.items():
        alias = field.validation_alias or field.alias
        names = alias_names(alias) if alias else [prefix + field_name]
        for name in names:
            yield name if case_sensitive else name.upper()


def alias_names(alias: Any) -> list[str]:
    """The variables an alias reads: a name; for an `AliasPath`, its first
    element; for `AliasChoices`, those of each choice."""
    if isinstance(alias, str):
        return [alias]
    if path := getattr(alias, "path", None):  # AliasPath
        return [path[0]] if isinstance(path[0], str) else []
    choices = getattr(alias, "choices", None) or []  # AliasChoices
    return [name for choice in choices for name in alias_names(choice)]


def instances_created_at_import(
    settings_class: Any, already_loaded: set[str]
) -> dict[str, Any]:
    """The instances of the class bound in the modules imported with it,
    and in its own module, by where they are (module.name): they read the
    machine's settings."""
    module_names = (set(sys.modules) - already_loaded) | {settings_class.__module__}
    instances: dict[str, Any] = {}
    seen: set[int] = set()
    for module_name in sorted(module_names):
        module = sys.modules.get(module_name)
        for attribute, value in vars(module).items() if module else ():
            if type(value) is settings_class and id(value) not in seen:
                seen.add(id(value))
                instances[f"{module_name}.{attribute}"] = value
    return instances


def recreate(instance: Any, context: str) -> None:
    """Create the instance again, in place, from the cleaned environment:
    whoever imported it sees the new values."""
    try:
        instance.__init__()
    except ValueError as e:  # pydantic's ValidationError
        msg = (
            f"{context}, created at import, can't be created again without "
            f"the machine's settings. Give its fields defaults, or create it "
            f"when it's first needed.\n{e}"
        )
        raise pytest.UsageError(msg) from e
