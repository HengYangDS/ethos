from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import tools.ci.ci_templates as ci

if TYPE_CHECKING:
    from pathlib import Path


def test_emulator_timeout_preserves_partial_log_and_blocks(monkeypatch, tmp_path: Path) -> None:
    class Process:
        pid = 42

        def __init__(self) -> None:
            self.waits = 0

        def wait(self, *, timeout=None):
            self.waits += 1
            if self.waits == 1:
                raise ci.subprocess.TimeoutExpired(["emulator"], timeout)
            return -15

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            return None

    monkeypatch.setattr(ci.shutil, "which", lambda *_args, **_kwargs: "/bin/emulator")
    monkeypatch.setattr(ci.subprocess, "Popen", lambda *_args, **_kwargs: Process())
    result = ci.run_command(
        ["emulator"],
        cwd=tmp_path,
        env={},
        timeout_seconds=1,
        log_path=tmp_path / "emulator.log",
        dry_run=False,
    )
    assert result["returncode"] == 124
    assert result["timed_out"] is True
    assert "timed out" in result["stderr"]


@pytest.mark.parametrize(("mode", "expected"), [("doctor", 0), ("run", 127)])
def test_missing_emulator_is_observable_and_never_claims_hosted_success(
    monkeypatch, tmp_path: Path, mode: str, expected: int
) -> None:
    monkeypatch.setattr(ci.shutil, "which", lambda *_args, **_kwargs: None)
    output = tmp_path / f"{mode}.json"
    assert (
        ci.emulator_evidence(
            "gitlab", mode=mode, dry_run=False, allow_untracked=mode == "run", output=output
        )
        == expected
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["returncode"] == 127
    assert payload["hosted_gitlab_status_claimed"] is False
    assert payload["verdict"] == ("pass" if mode == "doctor" else "block")
