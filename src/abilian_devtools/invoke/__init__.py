"""Experimental: reusable invoke tasks."""

from collections.abc import Sequence
from typing import Any

from invoke import task

from . import help, versions

MODULES = [help, versions]


def import_tasks(namespace: dict[str, Any], modules: Sequence[str] | None = None):
    """Import tasks from other modules."""
    if modules is None:
        modules_ = MODULES
    else:
        modules_ = [globals()[module_name] for module_name in modules]
    for module in modules_:
        import_tasks_from_module(namespace, module)


def import_tasks_from_module(namespace, module):
    for task_name in module.TASKS:
        task_ = getattr(module, task_name)
        namespace[task_.__name__] = task(task_)
