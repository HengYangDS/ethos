"""The record retirement preview plans unnamed old records and writes nothing else."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import pytest
from filelock import FileLock

import ethos.application.retention as retention
from ethos.adapters.store.state.schema import local_state_root
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.retention_store import archive
from tests.support.retention_store import lane_unit
from tests.support.retention_store import merge_preimage
from tests.support.retention_store import native_attempt
from tests.support.retention_store import proof_check
from tests.support.retention_store import put


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a governed repository whose preview runs as the selected runtime."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    monkeypatch.setattr(retention, "runtime_selected", lambda _root: True)
    return repo


def _plan(result: Any) -> dict[str, Any]:
    return json.loads(Path(result.data["plan"]["path"]).read_bytes())


def test_the_preview_plans_only_unnamed_old_records(repo: Path) -> None:
    """Named, young and foreign records stay; old unnamed ones enter the plan with their facts."""
    store = local_state_root(repo)
    old = put(store, "artifacts", proof_check(), ".json", age_days=30)
    young = put(store, "artifacts", proof_check("c" * 40), ".json", age_days=1)
    reached = put(store, "artifacts", merge_preimage(), ".json", age_days=30)
    named = put(store, "artifacts", native_attempt(reached.stem.encode()), ".zip", age_days=30)
    in_tree = put(store, "artifacts", merge_preimage("tree"), ".json", age_days=30)
    # A kept record names `named` in base64 inside a zip; `named` names `reached` in turn.
    encoded = base64.b64encode(named.stem.encode())
    put(store, "custody", archive({"evidence.txt": encoded}), ".zip", age_days=30)
    old_unit, _digest = lane_unit(store, "work/old", age_days=30)
    (repo / "notes.md").write_text(f"recovery evidence {in_tree.stem}\n", encoding="utf-8")
    commit_fixture(repo, "record a store digest in the accepted tree")
    foreign = put(store, "artifacts", b'{"producer": "other"}', ".json", age_days=30)

    result = retention.preview_record_retirement(repo)

    assert result.verdict == "pass", result
    plan = _plan(result)
    planned = {Path(entry["path"]) for item in plan["items"] for entry in item["files"]}
    assert planned == {old, old_unit["request"], old_unit["receipt"]}
    assert not planned & {young, named, reached, in_tree, foreign}
    assert plan["accepted_commit"] == git(repo, "rev-parse", "dev")
    assert set(plan["cutoffs"]) == {"artifact", "record"}
    first = next(item for item in plan["items"] if item["kind"] == "proof-check")
    assert first["state"] == "artifact"
    assert first["files"] == [
        {
            "path": old.as_posix(),
            "size": old.stat().st_size,
            "mtime_ns": str(old.stat().st_mtime_ns),
        }
    ]
    assert result.summary["candidates"] == {"proof-check": 1, "lane-retirement": 1}
    unowned = [dict(entry) for entry in result.data["unowned"]]
    assert unowned == [{"path": foreign.as_posix(), "bytes": foreign.stat().st_size}]
    assert old.exists()


def test_a_live_member_keeps_the_record_it_names(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A live Attestation member is a root like any kept store file."""
    store = local_state_root(repo)
    record = put(store, "artifacts", proof_check(), ".json", age_days=30)
    monkeypatch.setattr(retention, "live_member_bytes", lambda _root: [record.stem.encode()])

    plan = _plan(retention.preview_record_retirement(repo))

    assert plan["items"] == []


@pytest.mark.parametrize("refusal", ["runtime", "floor", "slot", "carrier"])
def test_the_preview_refuses_and_writes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, refusal: str
) -> None:
    """Another runtime, an unreadable floor, a held proof slot or an unreadable carrier refuse."""
    store = local_state_root(repo)
    put(store, "artifacts", proof_check(), ".json", age_days=30)
    if refusal == "runtime":
        monkeypatch.setattr(retention, "runtime_selected", lambda _root: False)
    elif refusal == "floor":
        (repo / ".ethos/rules.toml").write_text("[paradigm.retention\n", encoding="utf-8")
        commit_fixture(repo, "damage the accepted binding")
    elif refusal == "carrier":
        put(store, "custody", b"PK\x03\x04 damaged", ".zip", age_days=30)
    slot = FileLock(str(store / "proof-slot.lock"))
    if refusal == "slot":
        slot.acquire()
    try:
        result = retention.preview_record_retirement(repo)
    finally:
        if refusal == "slot":
            slot.release()

    gap = {
        "runtime": "record_retirement_runtime_unselected",
        "floor": "record_retirement_floor_unreadable",
        "slot": "record_retirement_proof_slot_held",
        "carrier": "record_retirement_carrier_undecodable",
    }[refusal]
    assert result.verdict == "block", result
    assert any(code.startswith(gap) for code in result.required_gaps), result.required_gaps
    assert not (store / "requests/record-retirement").exists()
