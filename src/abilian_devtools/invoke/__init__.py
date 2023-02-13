"""
Experimental: reusable invoke tasks.
"""

from invoke import task

from . import help, versions


def import_tasks(namespace):
    """Import tasks from other modules."""
    for module in [help, versions]:
        for task_name in module.TASKS:
            _task = getattr(module, task_name)
            namespace[_task.__name__] = task(_task)
