"""Build a verified exported handoff between independent native repositories."""

from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    import pytest

from ethos.adapters.mutation.lane_lifecycle.handoff.transfer import export_cross_host_handoff
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CrossHostHandoffExportRequest
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LaneLease
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_active_commitment


def export_handoff_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_holder: str,
    target_holder: str,
    branch: str,
) -> tuple[Any, Any, Path, str, dict[str, object]]:
    source_repo, _candidate = start_adopted_candidate(tmp_path / "source")
    destination = tmp_path / "destination" / "repo"
    destination.parent.mkdir()
    subprocess.run(
        ["git", "clone", "--no-local", source_repo.as_posix(), destination.as_posix()],
        check=True,
        text=True,
        capture_output=True,
    )
    git(destination, "config", "commit.gpgsign", "false")
    git(destination, "config", "core.hooksPath", ".git/test-hooks")
    git(
        destination,
        "worktree",
        "add",
        "-b",
        "candidate/dev",
        (tmp_path / "destination" / "repo-candidate-dev").as_posix(),
        "origin/candidate/dev",
    )
    source_worktree = tmp_path / "source-worktree"
    git(source_repo, "worktree", "add", "-b", branch, source_worktree.as_posix(), "dev")
    write_active_commitment(source_worktree, change_id="handoff")
    git(source_worktree, "add", ".")
    git(
        source_worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "declare handoff",
    )
    head = git(source_worktree, "rev-parse", "HEAD")
    now = datetime.now(UTC)
    lease = acquire_lease(
        state_database(source_worktree),
        lease=LaneLease(
            lane_ref=branch,
            holder_ref=HolderRef.parse(source_holder),
            generation=1,
            expires_at=now + timedelta(days=1),
        ),
    )
    source = SimpleNamespace(worktree=source_worktree)
    export_arguments = {
        "root": source.worktree.as_posix(),
        "branch": branch,
        "holder_ref": source_holder,
        "target_holder_ref": target_holder,
        "generation": int(lease["generation"]),
        "expires_at": str(lease["expires_at"]),
        "expect_head": head,
        "context_text": "Continue only after destination validates the package.",
        "context_file": None,
        "output_root": (tmp_path / "packages").as_posix(),
        "apply": True,
    }
    monkeypatch.setenv("ETHOS_ACTOR", source_holder)
    exported = export_cross_host_handoff(CrossHostHandoffExportRequest(**export_arguments))
    assert exported["verdict"] == "pass"
    assert exported["attestation"]["payload"]["body"]["result"]["state"] == "applied"
    manifest = exported["manifest"]
    expected_manifest = {
        "source_head": head,
        "source_tree": git(source_worktree, "rev-parse", "HEAD^{tree}"),
    }
    assert {key: manifest[key] for key in expected_manifest} == expected_manifest
    package = Path(str(exported["package_path"]))
    repeated_export = export_cross_host_handoff(CrossHostHandoffExportRequest(**export_arguments))
    assert repeated_export["package_id"] == exported["package_id"]
    assert repeated_export["attestation"]["payload"]["body"]["result"]["state"] == "recognized"
    return source, destination, package, head, lease
