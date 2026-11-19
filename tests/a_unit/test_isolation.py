"""The guard in the root conftest: no test reads the developer's machine."""

import os
from pathlib import Path

from abilian_devtools.seed import config


def test_the_global_config_is_not_the_developers(global_config_file: Path) -> None:
    assert global_config_file == config.GLOBAL_CONFIG_FILE
    assert not config.GLOBAL_CONFIG_FILE.is_relative_to(Path.home() / ".config")


def test_no_adt_variable_comes_from_the_shell() -> None:
    assert [name for name in os.environ if name.startswith("ADT_")] == []
