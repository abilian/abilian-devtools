"""Experimental: reusable invoke tasks."""

from collections.abc import Sequence
from typing import Any, Optional

from invoke import task

from . import help, versions

MODULES = [help, versions]


def import_tasks(namespace: dict[str, Any], modules: Optional[Sequence[str]] = None):
    """Import tasks from other modules."""
    if modules is None:
        _modules = MODULES
    else:
        _modules = [globals()[module_name] for module_name in modules]
    for module in _modules:
        import_tasks_from_module(namespace, module)


def import_tasks_from_module(namespace, module):
    for task_name in module.TASKS:
        _task = getattr(module, task_name)
        namespace[_task.__name__] = task(_task)
