# ruff: noqa: ARG005
from __future__ import annotations

import ast
import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import ethos.repository.evidence.parity.core as parity
from ethos.adapters.mutation import core
from ethos.adapters.mutation import lanes
from ethos.adapters.mutation.lane_lifecycle.core import default_candidate_path
from ethos.adapters.mutation.lane_lifecycle.core import slug
from ethos.adapters.store.retrieval import common as retrieval_common
from ethos.adapters.store.retrieval import indexing as retrieval_indexing
from ethos.adapters.store.retrieval import query as retrieval_query
from ethos.adapters.store.retrieval import schema as retrieval_schema
from ethos.adapters.store.retrieval import sources as retrieval_sources
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE


def cp(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


POLICY = SimpleNamespace(
    accepted_branch="dev",
    candidate_branch="candidate/dev",
    work_branch=lambda slug: f"work/{slug}",
)


def status_for(
    *,
    role: str = ROLE_WORK_LANE,
    dirty: bool = False,
    candidate: dict[str, object] | None = None,
    branch: str = "work/x",
) -> dict[str, object]:
    return {
        "role": role,
        "dirty": dirty,
        "branch": branch,
        "candidate": candidate
        or {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/workspace/candidate",
            "head": "c1",
        },
        "worktrees": [
            {"role": ROLE_ACCEPTED_ROOT, "path": "/repo", "branch": "dev", "head": "h0"},
            {"role": ROLE_WORK_LANE, "path": "/repo-w", "branch": branch, "head": "h1"},
        ],
    }


def test_mutation_decisions_and_candidate_base_edges(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        core, "workspace_status", lambda root: status_for(role=ROLE_ACCEPTED_ROOT, dirty=True)
    )
    monkeypatch.setattr(core, "executed_proof_record", lambda root, head: None)
    decision = core.evaluate_mutation(
        core.MutationRequest(command="land", apply=True, authorized=False, expect_head="other"),
        root=tmp_path,
        current_head="h1",
    )
    assert decision.gaps == (
        "authorization_required",
        "expect_head_mismatch",
        "protected_root_mutation",
        "proof_not_proven",
    )

    monkeypatch.setattr(core, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(core, "_git", lambda root, *args, check=True, **kwargs: cp(stdout="h1\n"))
    for candidate, gap in [
        (
            {"exists": False, "worktree_exists": False, "worktree_path": "", "head": ""},
            "candidate_branch_missing",
        ),
        (
            {"exists": True, "worktree_exists": False, "worktree_path": "", "head": "c1"},
            "candidate_worktree_missing",
        ),
    ]:
        monkeypatch.setattr(
            core,
            "workspace_status",
            lambda root, candidate=candidate: status_for(candidate=candidate),
        )
        assert core.candidate_base_report(root=tmp_path)["required_gaps"] == [gap]
    monkeypatch.setattr(
        core,
        "workspace_status",
        lambda root: status_for(dirty=(root.as_posix() == "/workspace/candidate")),
    )
    assert core.candidate_base_report(root=tmp_path)["required_gaps"] == [
        "candidate_worktree_dirty"
    ]
    monkeypatch.setattr(core, "workspace_status", lambda root: status_for())
    monkeypatch.setattr(core, "_is_ancestor", lambda root, ancestor, descendant: False)
    assert core.candidate_base_report(root=tmp_path)["required_gaps"] == ["candidate_base_stale"]


def test_lanes_helpers_claim_binding_bootstrap_and_refresh(monkeypatch, tmp_path: Path) -> None:
    assert slug("  A b@@c ") == "a-b-c"
    assert slug("@@") == "work"
    assert default_candidate_path(Path("/workspace/repo"), "candidate/dev") == Path(
        "/workspace/repo-candidate-dev"
    )
    status = status_for(branch="work/x")
    assert lanes._status_work_lane(status, "work/x")["branch"] == "work/x"
    assert lanes._status_work_lane({"worktrees": ["bad"]}, "work/x") is None
    assert lanes._state_root(status, tmp_path) == Path("/repo")
    monkeypatch.setattr(lanes, "active_leases", lambda db: [{"subject": "work/x", "owner": "me"}])
    assert lanes._active_lease(tmp_path / "state.sqlite", "work/x")["owner"] == "me"

    monkeypatch.setattr(lanes, "repo_root", lambda root: tmp_path)
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status)
    monkeypatch.setattr(lanes, "active_leases", lambda db: [])
    assert lanes.bind_work_lane_claim(root=tmp_path, claim_id="", apply=False)["required_gaps"] == [
        "missing_claim_id",
        "work_lane_missing_lease:work/x",
    ]
    monkeypatch.setattr(
        lanes, "active_leases", lambda db: [{"subject": "work/x", "owner": "me", "payload": {}}]
    )
    monkeypatch.setattr(
        lanes,
        "update_lease_payload",
        lambda db, subject, payload: {"owner": "me", "payload": payload},
    )
    assert (
        lanes.bind_work_lane_claim(root=tmp_path, claim_id="claim-1", apply=True)["state"]
        == "bound"
    )

    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(
        lanes, "run_git", lambda root, *args, check=True, **kwargs: cp(stdout="h1\n")
    )
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for(role=ROLE_ACCEPTED_ROOT))
    assert lanes.bootstrap_candidate(root=tmp_path, apply=True)["state"] == "present"
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for(role=ROLE_WORK_LANE))
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])
    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: True)
    assert lanes.refresh_work_lane_base(root=tmp_path, apply=False)["state"] == "base_current"
    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: False)
    assert (
        lanes.refresh_work_lane_base(root=tmp_path, apply=False)["state"] == "ready_to_refresh_base"
    )


def valid_shadow_evidence(tmp_path: Path, adopter: str = "generic") -> dict[str, object]:
    return parity.build_tracked_parity_evidence(
        adopter=adopter,
        target=tmp_path,
        shadow={"ok": True, "required_gaps": [], "accepted_summary": {"total_count": 1}},
        current_product_head="p1",
        current_target_head="t1",
        timeout_seconds=30,
    )


def test_parity_evidence_valid_invalid_and_stale(tmp_path: Path) -> None:
    assert (
        parity.parity_gaps_report(adopter="generic", root=tmp_path, target=tmp_path)["ok"] is False
    )
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "generic-shadow.json").write_text("not-json", encoding="utf-8")
    assert (
        "parity_evidence_invalid_json:JSONDecodeError"
        in parity.parity_gaps_report(adopter="generic", root=tmp_path, target=tmp_path)[
            "required_gaps"
        ]
    )
    payload = valid_shadow_evidence(tmp_path)
    (evidence_dir / "generic-shadow.json").write_text(json.dumps(payload), encoding="utf-8")
    assert (
        parity.parity_gaps_report(
            adopter="generic",
            root=tmp_path,
            target=tmp_path,
            current_product_head="p1",
            current_target_head="t1",
        )["ok"]
        is True
    )
    stale = parity.parity_gaps_report(
        adopter="generic",
        root=tmp_path,
        target=tmp_path,
        current_product_head="new",
        current_target_head="new",
    )
    assert any("product_head" in gap for gap in stale["required_gaps"])
    assert any("target_head" in gap for gap in stale["required_gaps"])


def test_shadow_parity_report_and_invalid_evidence(tmp_path: Path) -> None:
    evidence = valid_shadow_evidence(tmp_path, adopter="demo")
    path = parity.write_tracked_parity_evidence(root=tmp_path, adopter="demo", evidence=evidence)
    report = parity.shadow_parity_report(
        target=tmp_path,
        root=tmp_path,
        adopter="demo",
        current_product_head="p1",
        current_target_head="t1",
    )
    assert report["evidence_path"] == path.relative_to(tmp_path).as_posix()
    evidence["shadow"] = {"ok": False, "required_gaps": ["gap"]}
    path.write_text(json.dumps(evidence), encoding="utf-8")
    assert (
        parity.shadow_parity_report(target=tmp_path, root=tmp_path, adopter="demo")["state"]
        == "invalid"
    )
    assert (
        parity.shadow_parity_report(target=tmp_path, root=tmp_path, adopter=None)["state"]
        == "planned"
    )


def test_retrieval_helpers_context_eval_and_index_source(monkeypatch, tmp_path: Path) -> None:
    assert retrieval_sources.porcelain_paths('old -> "new path"') == ("old", "new path")
    assert retrieval_sources.is_allowed_source_rel("README.md") is True
    assert retrieval_sources.is_allowed_source_rel(".ethos/state/x") is False
    assert retrieval_indexing.language_for(Path("x.yaml")) == "yaml"
    assert retrieval_indexing.kind_for("openspec/specs/x.md", Path("x.md")) == "openspec"
    assert retrieval_query.fts_query_str("hello, world!") == "hello OR world"
    assert retrieval_indexing.signature_for(ast.parse("class C: pass").body[0]) == "class C"
    assert (
        retrieval_indexing.signature_for(ast.parse("async def f(a, b): pass").body[0])
        == "async def f(a, b)"
    )
    assert retrieval_indexing.python_symbols("def f(a):\n    return a\nclass C:\n    pass\n")
    assert retrieval_indexing.python_symbols("def broken(:\n") == []
    assert retrieval_indexing.chunks_for("README.md", "") == [
        {"title": "README.md", "text": "", "start_line": 1, "end_line": 1}
    ]
    assert (
        retrieval_sources.unsafe_source_reason(tmp_path, tmp_path / "missing.md") == "missing_path"
    )
    outside = tmp_path.parent / "outside.md"
    outside.write_text("x", encoding="utf-8")
    assert retrieval_sources.unsafe_source_reason(tmp_path, outside) == "path_outside_repository"

    assert retrieval_query.context_eval_report(tmp_path, suite="smoke")["required_gaps"] == [
        "context_index_missing"
    ]
    db = retrieval_common.default_retrieval_db_path(tmp_path)
    retrieval_schema.initialize_context_index(db)
    assert retrieval_common.latest_manifest_id(db) == "manifest:none"
    assert retrieval_common.latest_manifest_head(db) == "untracked"
    assert retrieval_query.context_eval_report(tmp_path, suite="deep")["required_gaps"] == [
        "context_eval_suite_missing"
    ]
    monkeypatch.setattr(
        retrieval_query,
        "search_context_index",
        lambda root, query, limit=10: {
            "ok": True,
            "selection": {"results": [], "diagnostics": [{"kind": "stale_candidate"}]},
            "summary": {"verified_count": 0},
        },
    )
    failed = retrieval_query.context_eval_report(
        tmp_path,
        suite="smoke",
        fixtures=({"id": "f1", "query": "q", "expected_paths": ("README.md",)},),
    )
    assert failed["required_gaps"] == ["context_eval_smoke_failed"]

    db2 = tmp_path / "retrieval.sqlite"
    retrieval_schema.initialize_context_index(db2)
    with closing(sqlite3.connect(db2)) as connection:
        connection.execute(
            "insert into index_manifests(id, root, head, schema_version, policy_digest, created_at, payload_json) values (?, ?, ?, ?, ?, ?, ?)",
            ("m1", tmp_path.as_posix(), "h1", 1, "p", "now", "{}"),
        )
        assert (
            retrieval_indexing.index_source(
                connection, tmp_path, "m1", tmp_path / "missing.py", "h1"
            )["chunk_count"]
            == 0
        )
        py = tmp_path / "module.py"
        py.write_text("# Title\n\ndef f(a):\n    return a\n", encoding="utf-8")
        counts = retrieval_indexing.index_source(connection, tmp_path, "m1", py, "h1")
    assert counts["chunk_count"] >= 1
    assert counts["symbol_count"] == 1
