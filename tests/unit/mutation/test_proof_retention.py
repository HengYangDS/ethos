from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.proof import apply_proof_retention
from ethos.adapters.mutation.proof import proof_retention_inventory
from ethos.adapters.mutation.proof import proof_state_dir

if TYPE_CHECKING:
    from pathlib import Path


def _proof(root: Path, head: str, *, record_head: str | None = None) -> Path:
    path = proof_state_dir(root) / f"{head}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": 3, "head": record_head or head, "state": "proven"}),
        encoding="utf-8",
    )
    return path


def test_proof_retention_preserves_protected_and_reachable_heads(
    tmp_path: Path,
) -> None:
    current = "a" * 40
    ref_reachable = "b" * 40
    worktree = "c" * 40
    live_lease = "d" * 40
    unreachable = "e" * 40
    for head in (current, ref_reachable, worktree, live_lease, unreachable):
        _proof(tmp_path, head)

    inventory = proof_retention_inventory(
        tmp_path,
        reachable_heads={current, ref_reachable},
        protected_heads={current, worktree, live_lease},
    )

    assert [item["head"] for item in inventory["delete_candidates"]] == [unreachable]
    assert {item["head"] for item in inventory["retained"]} == {
        current,
        ref_reachable,
        worktree,
        live_lease,
    }


def test_proof_retention_reports_malformed_records_without_deleting_them(
    tmp_path: Path,
) -> None:
    malformed_name = _proof(tmp_path, "not-a-head")
    mismatched = _proof(tmp_path, "f" * 40, record_head="0" * 40)
    invalid_json = proof_state_dir(tmp_path) / f"{'1' * 40}.json"
    invalid_json.write_text("{", encoding="utf-8")

    inventory = proof_retention_inventory(
        tmp_path,
        reachable_heads=set(),
        protected_heads=set(),
    )

    assert inventory["delete_candidates"] == []
    assert {item["path"] for item in inventory["invalid"]} == {
        malformed_name.relative_to(tmp_path).as_posix(),
        mismatched.relative_to(tmp_path).as_posix(),
        invalid_json.relative_to(tmp_path).as_posix(),
    }


def test_apply_proof_retention_deletes_only_exact_digest_matches(
    tmp_path: Path,
) -> None:
    head = "e" * 40
    path = _proof(tmp_path, head)
    inventory = proof_retention_inventory(
        tmp_path,
        reachable_heads=set(),
        protected_heads=set(),
    )

    deleted = apply_proof_retention(tmp_path, inventory["delete_candidates"])

    assert deleted == [path.relative_to(tmp_path).as_posix()]
    assert not path.exists()


def test_apply_proof_retention_fails_closed_on_content_drift(tmp_path: Path) -> None:
    head = "e" * 40
    path = _proof(tmp_path, head)
    inventory = proof_retention_inventory(
        tmp_path,
        reachable_heads=set(),
        protected_heads=set(),
    )
    path.write_text('{"head":"changed"}', encoding="utf-8")

    with pytest.raises(ValueError, match="proof_retention_candidate_drift"):
        apply_proof_retention(tmp_path, inventory["delete_candidates"])

    assert path.exists()
    assert (
        inventory["delete_candidates"][0]["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest()
    )
