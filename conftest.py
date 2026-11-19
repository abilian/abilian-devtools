"""The tests read nothing of the developer's machine.

At the repository root, so it covers every test below it.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def global_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where `~/.config/adt/config.toml` is, for a test: an absent file in its
    temporary directory, which a test may write. Also removes the `ADT_*`
    variables of the developer's shell, which seed reads."""
    path = tmp_path / "global-config" / "config.toml"
    monkeypatch.setattr("abilian_devtools.seed.config.GLOBAL_CONFIG_FILE", path)
    for name in list(os.environ):
        if name.startswith("ADT_"):
            monkeypatch.delenv(name)
    return path
