"""A process holding an empty directory open does not keep reviewed retirement content in use."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from tests.support.lane_scenarios import apply_retirement_receipt
from tests.support.lane_scenarios import derive_abandonment

if TYPE_CHECKING:
    from pathlib import Path

_HOLDER = """import os, sys
descriptor = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
print('ready', flush=True)
sys.stdin.read(1)
os.close(descriptor)
"""


@pytest.mark.skipif(os.name != "posix", reason="native POSIX process-reference observation")
@pytest.mark.parametrize("entries", [0, 1])
def test_retirement_removes_an_empty_directory_another_process_holds(
    divergent_lane: tuple[Path, Path], entries: int
) -> None:
    """An agent's empty host-local directory loses nothing; held content still blocks."""
    repo, lane = divergent_lane
    (lane / "build").mkdir()
    (lane / "build" / "output.txt").write_text("ignored output\n", encoding="utf-8")
    held = lane / ".claude" / ".cc-writes"
    held.mkdir(parents=True)
    if entries:
        (held / "record").write_text("host-local record\n", encoding="utf-8")
    derived = derive_abandonment(repo, review_content=True)
    assert derived["verdict"] == "pass", json.dumps(derived, indent=2)
    receipt = derived["receipt"]
    assert isinstance(receipt, dict)

    with subprocess.Popen(
        [sys.executable, "-B", "-c", _HOLDER, str(held)],
        cwd=repo,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    ) as holder:
        assert holder.stdin is not None
        assert holder.stdout is not None
        try:
            assert select.select([holder.stdout], [], [], 10)[0], "holder did not become ready"
            assert holder.stdout.readline() == "ready\n"
            result = apply_retirement_receipt(repo, receipt)
        finally:
            holder.communicate("x", timeout=10)

    if entries:
        assert result["required_gaps"] == ["retirement_content_in_use"], json.dumps(result)
        assert (held / "record").is_file()
    else:
        assert result["verdict"] == "pass", json.dumps(result, indent=2)
        assert not lane.exists()
