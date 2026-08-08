"""Bounded Git hook transaction runtime projection."""

from __future__ import annotations

import shutil
import sys
import uuid
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import distribution
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import HOOK_NAMES

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def initiating_hook_transaction(root: Path) -> Iterator[dict[str, str]]:
    """Create one exact current-process hook projection for a bounded Git transaction."""
    executable = Path(sys.executable)
    try:
        package = distribution("ethos")
    except PackageNotFoundError as error:
        message = "hook_transaction_distribution_missing"
        raise ValueError(message) from error
    prefix = Path(sys.prefix).resolve()
    location = Path(str(package.locate_file(""))).resolve()
    if (
        not executable.is_absolute()
        or not executable.is_file()
        or not location.is_relative_to(prefix)
        or not package.version
    ):
        message = "hook_transaction_runtime_invalid"
        raise ValueError(message)
    hooks = Path(git_common_dir(root)) / "ethos" / "transactions" / uuid.uuid4().hex / "hooks"
    hooks.mkdir(parents=True)
    launcher = (
        "#!/bin/sh\n"
        "# Generated for one ETHOS Git transaction.\n"
        f'exec "{executable.as_posix()}" -I -m ethos.cli hook run "$0" "$@"\n'
    )
    try:
        for name in HOOK_NAMES:
            target = hooks / name
            target.write_text(launcher.replace('"$0"', name), encoding="utf-8", newline="\n")
            target.chmod(0o755)
        yield {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": hooks.as_posix(),
        }
    finally:
        shutil.rmtree(hooks.parent, ignore_errors=True)
