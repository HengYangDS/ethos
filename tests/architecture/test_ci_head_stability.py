from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from tests.support.contract_helpers import git as _git

ROOT = Path(__file__).resolve().parents[2]
HEAD_GUARD = ROOT / "tools/ci/scripts/require-stable-head.sh"
LOCAL_CI = ROOT / "tools/ci/scripts/run-local-ci.sh"


def _commit(repo: Path, filename: str, content: str, message: str) -> str:
    path = repo / filename
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def test_head_stability_guard_rejects_evidence_after_head_moves(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "ETHOS Test")
    _git(repo, "config", "user.email", "ethos-test@example.invalid")
    first_head = _commit(repo, "tracked.txt", "one\n", "first")

    guard = tmp_path / "require-stable-head.sh"
    shutil.copy2(HEAD_GUARD, guard)
    captured_head = subprocess.run(
        [guard.as_posix(), "capture"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert captured_head == first_head

    second_head = _commit(repo, "tracked.txt", "two\n", "second")
    result = subprocess.run(
        [guard.as_posix(), "verify", captured_head, "test evidence run"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert first_head in result.stderr
    assert second_head in result.stderr
    assert "discard this evidence and rerun on a stable head" in result.stderr


def test_local_ci_fails_closed_when_head_changes_during_run() -> None:
    script = LOCAL_CI.read_text(encoding="utf-8")

    assert "tools/ci/scripts/require-stable-head.sh capture" in script
    assert "tools/ci/scripts/require-stable-head.sh verify" in script
    assert "trap _ethos_verify_local_ci_head_stability EXIT" in script
    assert script.index("run-python-tests") < script.index("run-local-state-audit")


def test_local_ci_writes_head_bound_fallback_manifest() -> None:
    script = LOCAL_CI.read_text(encoding="utf-8")

    assert "build/evidence/local-ci/fallback.json" in script
    assert "ethos_local_ci_fallback_evidence" in script
    assert "ethos_local_ci_head" in script
    assert "head_stability" in script
