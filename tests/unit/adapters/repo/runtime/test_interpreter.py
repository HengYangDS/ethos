"""Every Python process that ETHOS starts runs isolated and in UTF-8 mode."""

from __future__ import annotations

import subprocess
import sys

from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS


def test_started_python_is_isolated_and_reads_and_writes_utf8() -> None:
    """The interpreter flags select isolation and UTF-8 mode whatever the host locale."""
    completed = subprocess.run(
        (
            sys.executable,
            *PYTHON_FLAGS,
            "-c",
            "import sys;print(sys.flags.isolated,sys.flags.utf8_mode)",
        ),
        capture_output=True,
        check=True,
        encoding="utf-8",
    )
    assert completed.stdout.split() == ["1", "1"]
