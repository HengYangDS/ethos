# ruff: noqa: ARG005, TC003, FBT003, PT011, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.store.state.events as state_events
import ethos.adapters.store.state.events as state_schema
import ethos.adapters.store.state.lease.lifecycle.core as state
import ethos.adapters.store.state.lease.lifecycle.effects as state_effects
import ethos.adapters.store.state.lease.projection as state_projection
import ethos.adapters.store.state.lease.projection as state_read
from ethos.adapters.mutation import core as mutation_core
from ethos.adapters.mutation import proof as mutation_proof
from ethos.adapters.mutation.closeout import core as closeout_core
from ethos.adapters.repo import coordination
from ethos.adapters.repo import git
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import BranchRolePolicy
from tests.support.subprocesses import completed as cp

POLICY = SimpleNamespace(
    release_branch="main",
    release_mirror="independent",
    accepted_branch="dev",
    candidate_branch="candidate/dev",
    submit_branch_for_source=lambda branch: f"submit/{branch.replace('/', '-')}",
)


def status_for(
    *,
    role: str = ROLE_WORK_LANE,
    dirty: bool = False,
    candidate: dict[str, object] | None = None,
    closeout_gaps: list[str] | None = None,
) -> dict[str, object]:
    return {
        "role": role,
        "dirty": dirty,
        "branch": "work/x" if role == ROLE_WORK_LANE else "dev",
        "changed_paths": [],
        "candidate": candidate
        or {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/workspace/candidate",
            "head": "c1",
        },
        "closeout_support": {"required_gaps": closeout_gaps or []},
    }


def accepted_status() -> dict[str, object]:
    return status_for(
        role=ROLE_ACCEPTED_ROOT,
        candidate={
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/workspace/c",
            "head": "c2",
        },
    )


def prepare_accepted_closeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mutation_core, "load_branch_role_policy", lambda root, *args: POLICY)
    monkeypatch.setattr(
        mutation_core,
        "evaluate_closeout_mutation",
        lambda *args, **kwargs: mutation_core.MutationEvaluation(ok=True, state="closeout_ready"),
    )
    monkeypatch.setattr(
        mutation_core, "workspace_status", lambda root, **_kwargs: accepted_status()
    )
    monkeypatch.setattr(mutation_core, "is_ancestor", lambda root, ancestor, descendant: True)
    monkeypatch.setattr(
        mutation_core,
        "carry_executed_proof_record",
        lambda **kwargs: {"ok": True, "state": "carried", "required_gaps": []},
    )


def evidence_for(head: str, runs: list[dict[str, object]] | None = None) -> dict[str, object]:
    body = {
        "id": "e1",
        "head": head,
        "durability": "local",
        "runs": runs
        or [{"id": "g", "verdict": "passed", "state": "proven", "trust_bearing": True}],
    }
    body["digest"] = mutation_proof._evidence_digest(body)
    return body


def test_mutation_proof_record_rejects_forgery_and_accepts_sealed(
    tmp_path: Path,
) -> None:
    assert mutation_proof.executed_proof_record(tmp_path, "h1") is None
    evidence = evidence_for("h1")
    path = mutation_proof.record_executed_proof(tmp_path, evidence)
    assert mutation_proof.executed_proof_record(tmp_path, "h1") is not None
    record = json.loads(path.read_text(encoding="utf-8"))
    record["evidence"]["runs"][0]["verdict"] = "failed"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert mutation_proof.executed_proof_record(tmp_path, "h1") is None
    path.write_text("{bad", encoding="utf-8")
    assert mutation_proof.executed_proof_record(tmp_path, "h1") is None
    path.write_text(json.dumps({"state": "proven", "head": "other"}), encoding="utf-8")
    assert mutation_proof.executed_proof_record(tmp_path, "h1") is None
    assert mutation_proof._runs_prove_head([]) is False
    assert mutation_proof._runs_prove_head(["bad"]) is False
    assert mutation_proof._runs_prove_head([{"verdict": "passed", "trust_bearing": False}]) is False
    assert (
        mutation_proof._runs_prove_head(
            [{"verdict": "passed", "trust_bearing": True, "state": "executed"}]
        )
        is False
    )


def test_mutation_proof_record_merges_same_head_gate_runs(tmp_path: Path) -> None:
    first = evidence_for(
        "h1",
        [
            {
                "action_id": "repository-audit",
                "verdict": "passed",
                "state": "proven",
                "trust_bearing": True,
            }
        ],
    )
    second = evidence_for(
        "h1",
        [
            {
                "action_id": "claims",
                "verdict": "passed",
                "state": "proven",
                "trust_bearing": True,
            }
        ],
    )

    mutation_proof.record_executed_proof(tmp_path, first)
    path = mutation_proof.record_executed_proof(tmp_path, second)

    record = mutation_proof.executed_proof_record(tmp_path, "h1")
    assert record is not None
    evidence = record["evidence"]
    runs = evidence["runs"]
    assert [run["action_id"] for run in runs] == ["repository-audit", "claims"]
    assert evidence["digest"] == mutation_proof._evidence_digest(evidence)
    assert json.loads(path.read_text(encoding="utf-8"))["evidence_digest"] == evidence["digest"]


def test_mutation_proof_merge_handles_legacy_index_and_invalid_runs() -> None:
    existing = {
        "id": "old",
        "head": "h1",
        "durability": "local",
        "runs": [
            {
                "id": "legacy-gate",
                "verdict": "passed",
                "state": "proven",
                "trust_bearing": True,
            },
            "not-a-run",
            {"verdict": "passed", "state": "proven", "trust_bearing": True},
        ],
    }
    incoming = {
        "id": "new",
        "head": "h1",
        "durability": "local",
        "runs": [
            {
                "id": "legacy-gate",
                "verdict": "passed",
                "state": "proven",
                "trust_bearing": True,
                "refreshed": True,
            },
            {"verdict": "passed", "state": "proven", "trust_bearing": True},
        ],
    }

    merged = mutation_proof._merge_same_head_evidence(existing, incoming)

    assert merged["id"] == "new"
    assert merged["head"] == "h1"
    assert merged["durability"] == "local"
    assert merged["runs"] == [
        {
            "id": "legacy-gate",
            "verdict": "passed",
            "state": "proven",
            "trust_bearing": True,
            "refreshed": True,
        },
        {"verdict": "passed", "state": "proven", "trust_bearing": True},
        {"verdict": "passed", "state": "proven", "trust_bearing": True},
    ]
    assert merged["digest"] == mutation_proof._evidence_digest(merged)
    assert (
        mutation_proof._merge_same_head_evidence({"runs": "bad"}, incoming)["runs"]
        == incoming["runs"]
    )


def test_mutation_proof_record_carries_only_verified_records(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    missing = mutation_proof.carry_executed_proof_record(
        source_root=source, target_root=target, head="h1"
    )
    assert missing["state"] == "skipped"
    assert missing["truth_boundary"] == "local-proof-state-projection"
    assert missing["mints_proof"] is False
    assert missing["same_head_only"] is True
    assert missing["source_verified"] is False
    assert missing["target_verified"] is False
    assert missing["required_gaps"] == ["proof_not_proven"]

    mutation_proof.record_executed_proof(source, evidence_for("h1"))
    carried = mutation_proof.carry_executed_proof_record(
        source_root=source, target_root=target, head="h1"
    )

    assert carried["ok"] is True
    assert carried["state"] == "carried"
    assert carried["truth_boundary"] == "local-proof-state-projection"
    assert carried["mints_proof"] is False
    assert carried["same_head_only"] is True
    assert carried["source_verified"] is True
    assert carried["target_verified"] is True
    assert mutation_proof.executed_proof_record(target, "h1") is not None


def test_promotion_completeness_surfaces_adopter_code_correctness_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    full = evidence_for(
        "h1",
        [
            {
                "action_id": "required",
                "verdict": "passed",
                "state": "proven",
                "trust_bearing": True,
            }
        ],
    )
    mutation_proof.record_executed_proof(tmp_path, full)
    monkeypatch.setattr(mutation_proof, "_promotion_required_gate_ids", lambda root: ("required",))
    monkeypatch.setattr(
        mutation_proof,
        "adopter_code_correctness_gaps",
        lambda root: ("adopter_code_correctness_missing",),
    )

    assert mutation_proof.promotion_completeness_gaps(tmp_path, "h1") == [
        "adopter_code_correctness_missing"
    ]


def test_mutation_core_apply_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mutation_core, "load_branch_role_policy", lambda root, *args: POLICY)
    monkeypatch.setattr(mutation_core, "proof_gaps", lambda root, head: [])
    monkeypatch.setattr(
        mutation_core,
        "workspace_status",
        lambda root, **_kwargs: status_for(closeout_gaps=["trust_gap"]),
    )
    decision = mutation_core.evaluate_mutation(
        mutation_core.MutationRequest("land", True, True, "h1"),
        root=tmp_path,
        current_head="h1",
    )
    assert decision.gaps == ("trust_gap",)

    ready_decision = mutation_core.MutationEvaluation(ok=True, state="land_ready")
    monkeypatch.setattr(mutation_core, "workspace_status", lambda root, **_kwargs: status_for())
    monkeypatch.setattr(
        mutation_core,
        "candidate_base_report",
        lambda root: {
            "ok": False,
            "required_gaps": ["candidate_base_stale"],
            "state": "blocked",
        },
    )
    monkeypatch.setattr(
        mutation_core,
        "run_git",
        lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0),
    )
    assert mutation_core.apply_land_to_candidate(
        root=tmp_path,
        authorized=True,
        expect_head="h1",
        admitted_decision=ready_decision,
    )["required_gaps"] == ["candidate_base_stale"]
    monkeypatch.setattr(
        mutation_core,
        "candidate_base_report",
        lambda root: {
            "ok": True,
            "path": str(tmp_path / "candidate"),
            "required_gaps": [],
        },
    )
    # The proof carry now runs BEFORE the ref move at both tails; stub it to succeed so
    # these white-box ordering tests exercise the git edges rather than proof presence.
    monkeypatch.setattr(
        mutation_core,
        "carry_executed_proof_record",
        lambda **kwargs: {"ok": True, "state": "carried", "required_gaps": []},
    )
    monkeypatch.setattr(mutation_core, "discard_executed_proof", lambda root, head: True)
    monkeypatch.setattr(
        mutation_core,
        "run_git",
        lambda root, *args, check=True, **kwargs: cp(
            stdout="h1\n",
            stderr="merge failed",
            returncode=1 if args[:1] == ("merge",) else 0,
        ),
    )
    assert mutation_core.apply_land_to_candidate(
        root=tmp_path,
        authorized=True,
        expect_head="h1",
        admitted_decision=ready_decision,
    )["required_gaps"] == ["candidate_update_failed"]
    merge_envs: list[dict[str, str] | None] = []

    def fake_land_git(root, *args, check=True, **kwargs):
        if args[:1] == ("merge",):
            merge_envs.append(kwargs.get("env"))
        return cp(stdout="h1\n", returncode=0)

    monkeypatch.setattr(mutation_core, "run_git", fake_land_git)
    assert (
        mutation_core.apply_land_to_candidate(
            root=tmp_path,
            authorized=True,
            expect_head="h1",
            admitted_decision=ready_decision,
        )["state"]
        == "candidate_validated"
    )
    # The candidate merge no longer carries a ref-move escape env — it earns admission
    # through the armed hook after the proof is pre-carried.
    assert merge_envs == [None]

    prepare_accepted_closeout(monkeypatch)
    monkeypatch.setattr(mutation_core, "is_ancestor", lambda root, ancestor, descendant: False)
    assert mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )["required_gaps"] == ["candidate_diverged_from_accepted"]
    monkeypatch.setattr(mutation_core, "is_ancestor", lambda root, ancestor, descendant: True)
    monkeypatch.setattr(
        mutation_core,
        "run_git",
        lambda root, *args, check=True, **kwargs: cp(
            stdout="h1\n",
            stderr="cannot lock ref",
            returncode=1 if args[:1] == ("update-ref",) else 0,
        ),
    )
    assert mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )["required_gaps"] == ["accepted_advanced_concurrently"]

    def fake_git_sync_failed(_root, *args, check=True, **_kwargs):
        _ = check
        reset_attempts = fake_git_sync_failed.reset_attempts
        if args[:1] == ("update-ref",):
            return cp(stdout="", returncode=0)
        if args[:2] == ("reset", "--hard"):
            fake_git_sync_failed.reset_attempts = reset_attempts + 1
            return cp(stdout="", stderr="sync failed", returncode=1)
        return cp(stdout="h1\n", returncode=0)

    fake_git_sync_failed.reset_attempts = 0
    monkeypatch.setattr(mutation_core, "run_git", fake_git_sync_failed)
    failed_sync = mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )
    assert failed_sync["required_gaps"] == ["accepted_worktree_sync_failed"]
    assert failed_sync["state"] == "blocked"
    assert failed_sync["sync_attempts"] == 1
    assert fake_git_sync_failed.reset_attempts == 1

    def fake_git_clean_after_sync(_root, *args, check=True, **_kwargs):
        _ = check
        if args[:1] == ("update-ref",):
            return cp(stdout="", returncode=0)
        if args[:2] == ("reset", "--hard"):
            return cp(stdout="", returncode=0)
        if args[:2] == ("status", "--short"):
            return cp(stdout="", returncode=0)
        return cp(stdout="h1\n", returncode=0)

    monkeypatch.setattr(mutation_core, "run_git", fake_git_clean_after_sync)
    assert (
        mutation_core.apply_candidate_to_accepted(root=tmp_path, authorized=True, expect_head="h1")[
            "state"
        ]
        == "accepted_validated"
    )


def test_release_mirror_closeout_edge_paths(monkeypatch, tmp_path):
    request = closeout_core.CloseoutRequest(
        root=tmp_path,
        policy=BranchRolePolicy(release_mirror="accepted_ff"),
        current_head="old",
        candidate_head="new",
        candidate_path=tmp_path,
        worktrees=[],
    )
    dependencies = closeout_core.CloseoutDependencies(
        run_git=lambda *_args, **_kwargs: cp(),
        is_ancestor=lambda *_args: True,
        carry_proof=lambda **_kwargs: {"ok": True, "required_gaps": []},
        discard_proof=lambda *_args: None,
    )
    promote = partial(
        closeout_core.promote_candidate_to_accepted,
        request,
        dependencies=dependencies,
    )
    assert promote()["required_gaps"][0] == "release_mirror_release_branch_missing"
    transition = closeout_core.CloseoutTransition("refs/heads/main", "old", "new", "new")
    worktrees = [{"branch": "main", "worktree_binding": "linked", "path": str(tmp_path)}]
    assert (
        closeout_core.sync_release_mirror(
            transition, worktrees, "new", "old", lambda *_a, **_k: cp()
        )["worktree_sync"]
        == "synced"
    )
    failed = closeout_core.sync_release_mirror(
        transition, worktrees, "new", "old", lambda *_a, **_k: cp(stderr="sync", returncode=1)
    )
    monkeypatch.setattr(closeout_core, "sync_release_mirror", lambda *_a: failed)
    assert closeout_core.promote_candidate_to_accepted(
        request,
        dependencies=closeout_core.CloseoutDependencies(
            run_git=lambda _r, *a, **_k: cp("old\n") if a[:1] == ("rev-parse",) else cp(),
            is_ancestor=lambda *_args: True,
            carry_proof=lambda **_k: {"ok": True, "required_gaps": []},
            discard_proof=lambda *_args: None,
        ),
    )["required_gaps"] == ["release_mirror_worktree_sync_failed"]
    assert closeout_core.proof_required_gaps({"required_gaps": "invalid"}) == ["proof_invalid"]
    assert closeout_core.proof_required_gaps(object()) == ["proof_invalid"]
    assert closeout_core.proof_carry_failure(request, object()) is not None


def test_closeout_retries_transient_accepted_worktree_sync_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prepare_accepted_closeout(monkeypatch)
    reset_attempts = {"count": 0}

    def fake_git_sync_retry(_root, *args, check=True, **_kwargs):
        _ = check
        if args[:1] == ("update-ref",):
            return cp(stdout="", returncode=0)
        if args[:2] == ("reset", "--hard"):
            reset_attempts["count"] += 1
            if reset_attempts["count"] == 1:
                return cp(stdout="", stderr="Unable to create index.lock", returncode=1)
            return cp(stdout="", returncode=0)
        if args[:2] == ("status", "--short"):
            return cp(stdout="", returncode=0)
        return cp(stdout="h1\n", returncode=0)

    monkeypatch.setattr(mutation_core, "run_git", fake_git_sync_retry)

    retried_sync = mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )

    assert retried_sync["state"] == "accepted_validated"
    assert retried_sync["sync_attempts"] == 2


def test_closeout_blocks_dirty_accepted_worktree_after_sync(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prepare_accepted_closeout(monkeypatch)

    def fake_git_dirty_after_sync(_root, *args, check=True, **_kwargs):
        _ = check
        if args[:1] == ("update-ref",):
            return cp(stdout="", returncode=0)
        if args[:2] == ("reset", "--hard"):
            return cp(stdout="", returncode=0)
        if args[:2] == ("status", "--short"):
            return cp(stdout=" M README.md\n", returncode=0)
        return cp(stdout="h1\n", returncode=0)

    monkeypatch.setattr(mutation_core, "run_git", fake_git_dirty_after_sync)

    dirty_after_sync = mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )

    assert dirty_after_sync["required_gaps"] == ["accepted_worktree_dirty_after_sync"]
    assert dirty_after_sync["state"] == "blocked"


def test_mutation_admission_blocks_unarchived_openspec_carriers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mutation_core, "proof_gaps", lambda root, head: [])
    monkeypatch.setattr(mutation_core, "is_ancestor", lambda root, ancestor, descendant: True)
    change = tmp_path / "openspec" / "changes" / "done"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text("- [x] done\n", encoding="utf-8")

    monkeypatch.setattr(mutation_core, "workspace_status", lambda root, **_kwargs: status_for())
    land_decision = mutation_core.evaluate_mutation(
        mutation_core.MutationRequest("land", True, True, "h1"),
        root=tmp_path,
        current_head="h1",
    )
    assert land_decision.gaps == ("openspec_completed_change_unarchived:done",)


def test_mutation_admission_blocks_any_active_openspec_carrier_before_land(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mutation_core, "proof_gaps", lambda root, head: [])
    change = tmp_path / "openspec" / "changes" / "wip"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text("- [x] started\n- [ ] not archived\n", encoding="utf-8")

    monkeypatch.setattr(mutation_core, "workspace_status", lambda root, **_kwargs: status_for())

    land_decision = mutation_core.evaluate_mutation(
        mutation_core.MutationRequest("land", True, True, "h1"),
        root=tmp_path,
        current_head="h1",
    )

    assert land_decision.gaps == ("openspec_active_change_unarchived:wip:work_lane",)


def test_mutation_admission_blocks_active_openspec_carriers_on_closeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mutation_core, "proof_gaps", lambda root, head: [])
    monkeypatch.setattr(mutation_core, "is_ancestor", lambda root, ancestor, descendant: True)
    change = tmp_path / "openspec" / "changes" / "wip"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text("- [ ] unfinished\n", encoding="utf-8")

    monkeypatch.setattr(
        mutation_core,
        "workspace_status",
        lambda root, **_kwargs: status_for(
            role=ROLE_ACCEPTED_ROOT,
            candidate={
                "exists": True,
                "worktree_exists": True,
                "worktree_path": str(tmp_path),
                "head": "h1",
            },
        ),
    )
    closeout_decision = mutation_core.evaluate_closeout_mutation(
        mutation_core.MutationRequest("closeout", False, False, "h1"),
        root=tmp_path,
        current_head="h1",
    )
    assert "openspec_active_change_unarchived:wip:accepted_root" in closeout_decision.gaps
    assert "openspec_active_change_unarchived:wip:candidate" in closeout_decision.gaps


def test_store_state_lease_events_and_malformed_rows(tmp_path: Path) -> None:
    db = tmp_path / ".ethos" / "state" / "state.sqlite"
    state_schema.initialize_state(db)
    assert state_events.safe_table("events") == "events"
    with pytest.raises(ValueError):
        state_events.safe_table("bad")
    assert "insert into events" in state_events.insert_event_sql("events")
    assert "from chronicle_events" in state_events.select_event_sql("chronicle_events")
    with closing(sqlite3.connect(db)) as connection, pytest.raises(ValueError):
        state_projection.table_columns(connection, "events")
    state_events.append_event(db, event_type="e", subject="s", payload={"x": 1})
    state_events.append_chronicle_event(db, event_type="c", subject="s", payload={"y": 2})
    assert state_events.list_events(db)[0]["payload"] == {"x": 1}
    assert state_events.list_chronicle_events(db)[0]["payload"] == {"y": 2}

    assert (
        state_effects.update_lease_payload(db, subject="missing", payload={"claim_id": "c"}) == {}
    )
    lease = state.acquire_lease(
        db,
        subject="work/x",
        holder_ref="agent:test:case:me",
        ttl_seconds=60,
        payload={"a": 1},
    )
    updated = state_effects.update_lease_payload(db, subject="work/x", payload={"claim_id": "c"})
    assert updated["payload"]["a"] == 1
    assert updated["payload"]["claim_id"] == "c"
    assert updated["payload"]["holder_ref"] == "agent:test:case:me"
    assert updated["payload"]["normalization_state"] == "normalized"
    assert state_read.active_leases(db)[0]["id"] == lease["id"]
    assert state_effects.delete_lease(db, subject="work/x") == 1
    assert state_read.active_leases(db) == []

    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values ('badtime','s','o','not-date','{}')"
        )
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values ('badjson','s','o','2999-01-01T00:00:00+00:00','[]')"
        )
        connection.commit()
    leases = state_read.active_leases(db)
    assert len(leases) == 1
    assert leases[0]["id"] == "badjson"
    assert leases[0]["subject"] == "s"
    assert leases[0]["expires_at"] == "2999-01-01T00:00:00+00:00"
    assert leases[0]["holder_ref"] == ""
    assert leases[0]["normalization_state"] == "legacy_ambiguous"
    assert leases[0]["payload"] == {}
    assert state_effects.delete_lease(tmp_path / "missing.sqlite", subject="x") == 0
    assert state_events.list_events(tmp_path / "missing.sqlite") == []


def test_git_and_coordination_edges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(git.subprocess, "run", lambda *args, **kwargs: cp(returncode=1))
    assert git.current_head(tmp_path) == "untracked"
    assert git.current_tracked_head(tmp_path) == ""
    assert git.git_stdout(tmp_path, "status") == ""
    assert git.git_files(tmp_path, "*.py") == []
    monkeypatch.setattr(git.subprocess, "run", lambda *args, **kwargs: cp(stdout=".git/common\n"))
    assert git.git_common_dir(tmp_path).endswith(".git/common")
    monkeypatch.setattr(git, "git_common_dir", lambda root: "same")
    assert git.same_git_repository(tmp_path, tmp_path / "other") is True

    monkeypatch.setattr(coordination.subprocess, "run", lambda *args, **kwargs: cp(returncode=1))
    assert coordination.branch_path_scope(
        tmp_path, branch="work/x", candidate_branch="candidate/dev"
    ) == ((), "unknown")
    monkeypatch.setattr(
        coordination.subprocess, "run", lambda *args, **kwargs: cp(stdout="docs/a.md\n")
    )
    assert coordination.branch_path_scope(
        tmp_path, branch="work/x", candidate_branch="candidate/dev"
    ) == (("docs/a.md",), "bounded")
    assert coordination.branch_path_scope(
        tmp_path, branch="detached", candidate_branch="candidate/dev"
    ) == ((), "unknown")
    assert coordination.path_overlaps("docs/a.md", "docs") is True
    assert coordination.scopes_overlap(("a/b",), ("a",)) is True
    assert (
        coordination.coordination_state(
            current_role="accepted_root",
            current_path_scope=(),
            current_scope_state="empty",
            foreign_path_scope=(),
            foreign_scope_state="empty",
        )
        == "advisory"
    )
    assert (
        coordination.coordination_state(
            current_role=ROLE_WORK_LANE,
            current_path_scope=("a",),
            current_scope_state="bounded",
            foreign_path_scope=("b",),
            foreign_scope_state="bounded",
        )
        == "disjoint"
    )
    assert (
        coordination.coordination_state(
            current_role=ROLE_WORK_LANE,
            current_path_scope=("a",),
            current_scope_state="deferred",
            foreign_path_scope=("b",),
            foreign_scope_state="bounded",
        )
        == "deferred"
    )
    required, advisory = coordination.coordination_gaps(
        [
            {
                "branch": "work/x",
                "lease_state": "missing",
                "coordination_state": "overlap",
            }
        ],
        current_role=ROLE_WORK_LANE,
        current_scope_state="unknown",
    )
    assert required == ["coordination_gap:current_scope_unknown"]
    assert "coordination_gap:scope_overlap:work/x" in advisory
    deferred_lane = coordination.foreign_work_lane_deferred(
        {
            "path": "/workspace/foreign",
            "head": "h1",
            "branch": "work/foreign",
            "role": ROLE_WORK_LANE,
            "worktree_binding": "linked",
        },
        lease={"holder_ref": "agent:test:case:foreign"},
        claim_id="claim",
        dirty_paths=("unobserved",),
    )
    assert deferred_lane["scope_state"] == "deferred"
    assert deferred_lane["coordination_state"] == "advisory"
    assert deferred_lane["closeout_disposition"] == "none"
    assert coordination._combined_scope_state("deferred", ("a",)) == "deferred"  # noqa: RUF100, SLF001 - exact deferred-scope reducer coverage
    package = coordination.coordination_package(
        [{"lease_state": "missing", "coordination_state": "unknown"}],
        required_gaps=["g"],
        advisory_gaps=["a"],
    )
    assert (
        package["blocking"] is True
        and package["missing_lease_count"] == 1
        and package["unknown_scope_count"] == 1
    )
    assert (
        package["next_action"]
        == "resolve required Work Lane coordination gaps before candidate integration"
    )
    residue_package = coordination.coordination_package(
        [
            {
                "branch": "work/landed-dirty",
                "lease_state": "leased",
                "coordination_state": "advisory",
                "closeout_disposition": "landed_dirty",
                "residue_state": "unpreserved_worktree_delta",
                "dirty": True,
            },
            {
                "branch": "work/retire-ready",
                "lease_state": "leased",
                "coordination_state": "advisory",
                "closeout_disposition": "retire_ready",
                "residue_state": "clean_or_none",
                "dirty": False,
            },
            {
                "branch": "work/none",
                "lease_state": "leased",
                "coordination_state": "advisory",
                "closeout_disposition": "none",
                "residue_state": "clean_or_none",
                "dirty": False,
            },
        ],
        required_gaps=[],
        advisory_gaps=["work_lane_closeout_residue_present"],
    )
    assert residue_package["closeout_residue_count"] == 2
    assert residue_package["dirty_closeout_residue_count"] == 1
    assert residue_package["closeout_residue_lanes"] == [
        {
            "branch": "work/landed-dirty",
            "closeout_disposition": "landed_dirty",
            "residue_state": "unpreserved_worktree_delta",
            "dirty": True,
        },
        {
            "branch": "work/retire-ready",
            "closeout_disposition": "retire_ready",
            "residue_state": "clean_or_none",
            "dirty": False,
        },
    ]
    unbound_package = coordination.coordination_package(
        [],
        required_gaps=[],
        advisory_gaps=["unbound_work_lane_ref_present"],
        unbound_work_lane_refs=[
            {
                "branch": "work/stale",
                "head": "abc123",
                "claim_id": "",
                "claim_binding": "missing",
                "relation_to_accepted": "diverged_from_accepted",
                "next_action": "inspect diverged unbound Work Lane ref before merge, supersede, or deletion",
            }
        ],
    )
    assert unbound_package["unbound_work_lane_count"] == 1
    assert unbound_package["unbound_work_lane_refs"][0]["branch"] == "work/stale"
    assert (
        unbound_package["next_action"]
        == "inspect or retire unbound Work Lane refs during coordination cleanup"
    )
    assert coordination.workspace_required_gaps(
        ["work_lane_missing_lease:work/x", "other"], candidate={"exists": False}
    ) == ["work_lane_missing_lease:work/x", "candidate_branch_missing"]
