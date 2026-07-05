# ruff: noqa: ARG005, TC003, FBT003, PT011, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.adapters.mutation import core as mutation_core
from ethos.adapters.mutation import proof as mutation_proof
from ethos.adapters.repo import coordination
from ethos.adapters.repo import git
from ethos.adapters.store import state
from ethos.domain import land
from ethos.repository.evidence import claims
from ethos.repository.registry import authority
from ethos_core.contracts.branch_roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


POLICY = SimpleNamespace(
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
            "worktree_path": "/tmp/candidate",
            "head": "c1",
        },
        "closeout_support": {"required_gaps": closeout_gaps or []},
    }


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


def test_mutation_proof_record_rejects_forgery_and_accepts_sealed(tmp_path: Path) -> None:
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


def test_mutation_core_apply_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(mutation_core, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(mutation_core, "_proof_gaps", lambda root, head: [])
    monkeypatch.setattr(
        mutation_core, "workspace_status", lambda root: status_for(closeout_gaps=["trust_gap"])
    )
    decision = mutation_core.evaluate_mutation(
        mutation_core.MutationRequest("land", True, True, "h1"), root=tmp_path, current_head="h1"
    )
    assert decision.gaps == ("trust_gap",)

    ready_decision = mutation_core.MutationDecision(ok=True, state="land_ready")
    monkeypatch.setattr(mutation_core, "workspace_status", lambda root: status_for())
    monkeypatch.setattr(
        mutation_core,
        "candidate_base_report",
        lambda root: {"ok": False, "required_gaps": ["candidate_base_stale"], "state": "blocked"},
    )
    monkeypatch.setattr(
        mutation_core,
        "_git",
        lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0),
    )
    assert mutation_core.apply_land_to_candidate(
        root=tmp_path, authorized=True, expect_head="h1", admitted_decision=ready_decision
    )["required_gaps"] == ["candidate_base_stale"]
    monkeypatch.setattr(
        mutation_core,
        "candidate_base_report",
        lambda root: {"ok": True, "path": str(tmp_path / "candidate"), "required_gaps": []},
    )
    monkeypatch.setattr(
        mutation_core,
        "_git",
        lambda root, *args, check=True, **kwargs: cp(
            stdout="h1\n", stderr="merge failed", returncode=1 if args[:1] == ("merge",) else 0
        ),
    )
    assert mutation_core.apply_land_to_candidate(
        root=tmp_path, authorized=True, expect_head="h1", admitted_decision=ready_decision
    )["required_gaps"] == ["candidate_update_failed"]
    monkeypatch.setattr(
        mutation_core,
        "_git",
        lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0),
    )
    assert (
        mutation_core.apply_land_to_candidate(
            root=tmp_path, authorized=True, expect_head="h1", admitted_decision=ready_decision
        )["state"]
        == "candidate_validated"
    )

    monkeypatch.setattr(
        mutation_core,
        "evaluate_closeout_mutation",
        lambda *args, **kwargs: mutation_core.MutationDecision(ok=True, state="closeout_ready"),
    )
    monkeypatch.setattr(
        mutation_core,
        "workspace_status",
        lambda root: status_for(
            role=ROLE_ACCEPTED_ROOT,
            candidate={
                "exists": True,
                "worktree_exists": True,
                "worktree_path": "/tmp/c",
                "head": "c2",
            },
        ),
    )
    monkeypatch.setattr(mutation_core, "_is_ancestor", lambda root, ancestor, descendant: False)
    assert mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )["required_gaps"] == ["candidate_diverged_from_accepted"]
    monkeypatch.setattr(mutation_core, "_is_ancestor", lambda root, ancestor, descendant: True)
    monkeypatch.setattr(
        mutation_core,
        "_git",
        lambda root, *args, check=True, **kwargs: cp(
            stdout="h1\n", stderr="ff failed", returncode=1 if args[:1] == ("merge",) else 0
        ),
    )
    assert mutation_core.apply_candidate_to_accepted(
        root=tmp_path, authorized=True, expect_head="h1"
    )["required_gaps"] == ["accepted_update_failed"]
    monkeypatch.setattr(
        mutation_core,
        "_git",
        lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0),
    )
    assert (
        mutation_core.apply_candidate_to_accepted(root=tmp_path, authorized=True, expect_head="h1")[
            "state"
        ]
        == "accepted_validated"
    )


def test_store_state_lease_events_and_malformed_rows(tmp_path: Path) -> None:
    db = tmp_path / ".ethos" / "state" / "state.sqlite"
    state.initialize_state(db)
    assert state._safe_table("events") == "events"
    with pytest.raises(ValueError):
        state._safe_table("bad")
    state.append_event(db, event_type="e", subject="s", payload={"x": 1})
    state.append_chronicle_event(db, event_type="c", subject="s", payload={"y": 2})
    assert state.list_events(db)[0]["payload"] == {"x": 1}
    assert state.list_chronicle_events(db)[0]["payload"] == {"y": 2}

    assert state.update_lease_payload(db, subject="missing", payload={"claim_id": "c"}) == {}
    lease = state.acquire_lease(db, subject="work/x", owner="me", ttl_seconds=60, payload={"a": 1})
    updated = state.update_lease_payload(db, subject="work/x", payload={"claim_id": "c"})
    assert updated["payload"] == {"a": 1, "claim_id": "c"}
    assert state.active_leases(db)[0]["id"] == lease["id"]
    assert state.delete_lease(db, subject="work/x") == 1
    assert state.active_leases(db) == []

    with sqlite3.connect(db) as connection:
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values ('badtime','s','o','not-date','{}')"
        )
        connection.execute(
            "insert into leases(id, subject, owner, expires_at, payload_json) values ('badjson','s','o','2999-01-01T00:00:00+00:00','[]')"
        )
        connection.commit()
    leases = state.active_leases(db)
    assert leases == [
        {
            "id": "badjson",
            "subject": "s",
            "owner": "o",
            "expires_at": "2999-01-01T00:00:00+00:00",
            "payload": {},
        }
    ]
    assert state.delete_lease(tmp_path / "missing.sqlite", subject="x") == 0
    assert state.list_events(tmp_path / "missing.sqlite") == []


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
    assert coordination.coordination_gaps(
        [{"branch": "work/x", "lease_state": "missing", "coordination_state": "overlap"}],
        current_role=ROLE_WORK_LANE,
        current_scope_state="unknown",
    )[0] == ["coordination_gap:current_scope_unknown", "coordination_gap:scope_overlap:work/x"]
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
    assert coordination.workspace_required_gaps(
        ["work_lane_missing_lease:work/x", "other"], candidate={"exists": False}
    ) == ["work_lane_missing_lease:work/x", "candidate_branch_missing"]


def test_claims_trust_envelope_and_report_edges(tmp_path: Path) -> None:
    assert claims.claims_report(tmp_path)["required_gaps"] == ["claims_missing"]
    assert claims._promotion_kind("docs/a.md") == "docs"
    assert claims._promotion_kind("schemas/a.json") == "schema"
    assert claims._promotion_kind("openspec/x") == "openspec"
    assert claims._promotion_kind("tests/a.py") == "tests"
    assert claims._promotion_targets(
        {"targets": ["docs/a.md", {"path": "src/a.py"}, {"path": "", "kind": "source"}]}
    ) == [
        {"kind": "docs", "path": "docs/a.md"},
        {"kind": "source", "path": "src/a.py"},
    ]
    assert claims._has_repository_overclaim("published and verified", "digest") is True
    assert claims._has_repository_overclaim("published and verified", "semantic") is False

    evidence = tmp_path / "evidence" / "proof.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("proof", encoding="utf-8")
    claim_dir = tmp_path / "evidence" / "claims"
    claim_dir.mkdir(parents=True)
    (claim_dir / "c1.toml").write_text(
        """
[claim]
id = "c1"
state = "active"
subject = "subject"
summary = "published and verified"

[evidence]
dated = "evidence/proof.md"
sha256 = "bad"
evidence_ids = []
binding = "raw/cache validates"
verifier = "digest"
head = "old"

[boundary]
owner = ""
scope = ""

[carriers]
openspec = "openspec/changes/missing"

[promotion]
targets = ["docs/missing.md"]
""".strip(),
        encoding="utf-8",
    )
    report = claims.claims_report(tmp_path, current_head="new")
    gaps = set(report["required_gaps"])
    assert "c1:evidence_ids_missing" in gaps
    assert "c1:semantic_overclaim_requires_semantic_verifier" in gaps
    assert "c1:evidence.sha256_mismatch" in gaps
    assert "c1:evidence.head_stale:old!=new" in gaps
    assert "c1:boundary.owner_missing" in gaps
    assert "c1:boundary.scope_missing" in gaps
    assert "c1:fallback_missing" in gaps
    assert "c1:kill_signal_missing" in gaps
    assert "c1:promotion_target_missing:docs/missing.md" in gaps


def test_land_publication_and_parity_head_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert (
        land.local_submit_package(branch="work/x", submit_branch="submit/x")["remote_state"]
        == "deferred"
    )
    assert land.publication_readiness(branch="work/x", local_ok=False, policy=POLICY)[
        "required_gaps"
    ] == ["local_publish_readiness_blocked"]
    monkeypatch.setattr(land, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(land, "workspace_status", lambda repo: {"candidate": {"head": "c1"}})
    monkeypatch.setattr(land._gitio, "current_tracked_head", lambda root: "h1")
    package = land.closeout_bootstrap_package(
        repo=tmp_path, audit_root=tmp_path / "candidate", required_gaps=("gap",)
    )
    assert package["blocking"] is True and "--expect-head h1" in package["command"]

    monkeypatch.setattr(
        land._gitio,
        "git_stdout",
        lambda root, *args: "h1 p1 p2" if args[:2] == ("rev-list", "--parents") else "h1",
    )
    assert land.acceptable_parity_product_heads(tmp_path, "generic") == ("h1", "p1", "p2")
    monkeypatch.setattr(land._gitio, "same_git_repository", lambda left, right: True)
    assert land.acceptable_parity_target_heads(tmp_path, tmp_path, "generic") == ("h1", "p1", "p2")
    monkeypatch.setattr(land._gitio, "current_tracked_head", lambda root: "")
    assert land.acceptable_parity_product_heads(tmp_path, "generic") == ()
    assert land.acceptable_parity_target_heads(tmp_path, tmp_path, "generic") == ()


def test_authority_graph_empty_entries_are_valid(tmp_path: Path) -> None:
    graph = tmp_path / "docs" / "_meta" / "authority_graph.toml"
    graph.parent.mkdir(parents=True)
    graph.write_text("", encoding="utf-8")

    report = authority.authority_graph_report(tmp_path)

    assert report["ok"] is True
    assert report["entries"] == []
    assert report["required_gaps"] == []
