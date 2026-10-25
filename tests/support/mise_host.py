"""Model a host on which the user's own decisions, not CI detection, set native mise trust."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.toolchain.mise import mise_executable

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# mise trusts every configuration while any CI marker is set, whatever its value: the generic
# markers, and those of the hosts that run these tests.
CI_MARKERS = (
    "CI",
    "CONTINUOUS_INTEGRATION",
    "BUILD_NUMBER",
    "RUN_ID",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "TF_BUILD",
)


def outside_ci(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """Hide CI detection, then require native mise to report the root untrusted."""
    for name in CI_MARKERS:
        monkeypatch.delenv(name, raising=False)
    native = (str(mise_executable()), "--cd", str(root), "trust", "--show")
    shown = run_command(root, native, timeout=30)
    assert ": untrusted" in shown.stdout, (
        "native mise reports the root trusted; another CI marker may be set",
        shown.stdout,
        shown.stderr,
    )
    assert ": trusted" not in shown.stdout, shown.stdout
