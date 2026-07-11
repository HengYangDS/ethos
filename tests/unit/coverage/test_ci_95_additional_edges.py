# ruff: noqa: ARG005, TC002, TC003, PT018
# Monkeypatch-heavy coverage edge tests intentionally preserve callable signatures
# matching patched runtime functions; unused parameters document those contracts.

from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.shadow.execution as shadow_execution
import ethos.adapters.shadow.semantics as shadow_semantics
import ethos.adapters.store.state.lease.lifecycle.core as state
import ethos.repository.evidence.parity.core as parity
from ethos.adapters.mutation import lanes
from ethos.adapters.store.retrieval import common as retrieval_common
from ethos.adapters.store.retrieval import indexing as retrieval_indexing
from ethos.adapters.store.retrieval import query as retrieval_query
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
    role: str = ROLE_ACCEPTED_ROOT,
    dirty: bool = False,
    candidate: dict[str, object] | None = None,
    worktrees: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "role": role,
        "dirty": dirty,
        "branch": "dev" if role == ROLE_ACCEPTED_ROOT else "work/x",
        "candidate": candidate
        or {
            "exists": True,
            "worktree_exists": True,
            "worktree_path": "/workspace/candidate",
            "head": "c1",
        },
        "worktrees": worktrees
        if worktrees is not None
        else [
            {
                "role": ROLE_ACCEPTED_ROOT,
                "path": "/repo",
                "branch": "dev",
                "head": "h0",
            },
            {
                "role": ROLE_WORK_LANE,
                "path": "/repo-w",
                "branch": "work/x",
                "head": "h1",
            },
        ],
    }


def test_start_work_lane_blocks_and_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(lanes, "repo_root", lambda root: tmp_path)
    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda root: POLICY)

    def start(**changes: object) -> dict[str, object]:
        return lanes.start_work_lane(
            **{
                "root": tmp_path,
                "name": "x",
                "path": tmp_path / "w",
                "holder_ref": "agent:test:case:me",
                **changes,
            }
        )

    assert start(name="My Lane", holder_ref="")["required_gaps"] == ["holder_ref_invalid"]
    planned = start(name="My Lane")
    assert planned["state"] == "planned"

    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for(role=ROLE_WORK_LANE))
    blocked = start(apply=True)
    assert blocked["required_gaps"] == ["lane_start_requires_clean_accepted_root"]

    for candidate, gap in [
        (
            {
                "exists": False,
                "worktree_exists": False,
                "worktree_path": "",
                "head": "",
            },
            "candidate_branch_missing",
        ),
        (
            {
                "exists": True,
                "worktree_exists": False,
                "worktree_path": "",
                "head": "c1",
            },
            "candidate_worktree_missing",
        ),
    ]:
        monkeypatch.setattr(
            lanes,
            "workspace_status",
            lambda root, candidate=candidate: status_for(candidate=candidate),
        )
        assert start(apply=True)["required_gaps"] == [gap]

    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for())
    monkeypatch.setattr(lanes, "changed_paths", lambda path: ["dirty.md"])
    assert start(apply=True)["required_gaps"] == ["candidate_worktree_dirty"]
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])
    monkeypatch.setattr(lanes, "_branch_exists", lambda root, branch: True)
    assert start(apply=True)["required_gaps"] == ["branch_already_exists"]
    monkeypatch.setattr(lanes, "_branch_exists", lambda root, branch: False)
    monkeypatch.setattr(
        lanes,
        "run_git",
        lambda root, *args, check=True, **kwargs: cp(stderr="nope", returncode=1),
    )
    assert start(apply=True)["required_gaps"] == ["worktree_add_failed"]

    def fake_git(
        root: Path, *args: str, check: bool = True, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("worktree", "add"):
            return cp(returncode=0)
        if args == ("rev-parse", "HEAD"):
            return cp(stdout="newhead\n")
        return cp()

    monkeypatch.setattr(lanes, "run_git", fake_git)
    monkeypatch.setattr(
        lanes,
        "acquire_lease",
        lambda *args, **kwargs: {
            "subject": kwargs["subject"],
            "holder_ref": kwargs["holder_ref"],
        },
    )
    started = start(claim_id="c", apply=True)
    assert started["state"] == "started"
    assert started["worktree"]["head"] == "newhead"


def test_candidate_refresh_bootstrap_and_retire_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(lanes, "repo_root", lambda root: tmp_path)
    monkeypatch.setattr(lanes, "load_branch_role_policy", lambda root: POLICY)
    monkeypatch.setattr(
        lanes, "run_git", lambda root, *args, check=True, **kwargs: cp(stdout="h1\n")
    )
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for(dirty=True))
    assert lanes.bootstrap_candidate(root=tmp_path, expect_head="other", apply=True)[
        "required_gaps"
    ] == [
        "candidate_bootstrap_requires_clean_accepted_root",
        "expect_head_mismatch",
    ]

    monkeypatch.setattr(
        lanes,
        "workspace_status",
        lambda root: status_for(
            candidate={
                "exists": False,
                "worktree_exists": False,
                "worktree_path": "",
                "head": "",
            }
        ),
    )
    target = tmp_path / "candidate"
    assert lanes.bootstrap_candidate(root=tmp_path, path=target, apply=False)["state"] == "planned"
    target.mkdir()
    assert lanes.bootstrap_candidate(root=tmp_path, path=target, apply=True)["required_gaps"] == [
        "candidate_worktree_path_exists"
    ]
    target.rmdir()

    def git_bootstrap(
        root: Path, *args: str, check: bool = True, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ("rev-parse", "HEAD"):
            return cp(stdout="h1\n")
        if args and args[0] == "branch":
            return cp(returncode=0)
        if args[:2] == ("worktree", "add"):
            return cp(returncode=1, stderr="cannot add")
        return cp()

    monkeypatch.setattr(lanes, "run_git", git_bootstrap)
    assert lanes.bootstrap_candidate(root=tmp_path, path=target, apply=True)["required_gaps"] == [
        "candidate_worktree_add_failed"
    ]

    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for())
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])
    monkeypatch.setattr(
        lanes,
        "run_git",
        lambda root, *args, check=True, **kwargs: cp(stdout="h1\n", returncode=0),
    )
    blocked = lanes.refresh_candidate_from_accepted(root=tmp_path, apply=True, authorized=False)
    assert set(blocked["required_gaps"]) == {
        "authorization_required",
        "expect_head_required",
    }
    assert (
        lanes.refresh_candidate_from_accepted(root=tmp_path, apply=False)["state"]
        == "ready_to_refresh_from_accepted"
    )
    refreshed = lanes.refresh_candidate_from_accepted(
        root=tmp_path, apply=True, authorized=True, expect_head="h1"
    )
    assert refreshed["state"] == "refreshed_from_accepted"

    worktrees = [
        {
            "role": ROLE_WORK_LANE,
            "path": str(tmp_path / "w"),
            "branch": "work/x",
            "head": "h2",
        },
    ]
    (tmp_path / "w").mkdir()
    monkeypatch.setattr(lanes, "workspace_status", lambda root: status_for(worktrees=worktrees))
    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: False)
    assert lanes.retire_landed_work_lanes(root=tmp_path, branch="missing")["required_gaps"] == [
        "retire_branch_not_found"
    ]
    assert lanes.retire_landed_work_lanes(root=tmp_path, apply=True)["required_gaps"] == [
        "retire_branch_required"
    ]
    assert (
        lanes.retire_landed_work_lanes(root=tmp_path, branch="work/x")["lanes"][0]["retire_ready"]
        is False
    )

    monkeypatch.setattr(lanes, "is_ancestor", lambda root, ancestor, descendant: True)
    monkeypatch.setattr(lanes, "changed_paths", lambda path: [])
    calls: list[tuple[str, ...]] = []

    def git_retire(
        root: Path, *args: str, check: bool = True, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return cp(returncode=0)

    monkeypatch.setattr(lanes, "run_git", git_retire)
    state.acquire_lease(
        tmp_path / ".ethos" / "state" / "state.sqlite",
        subject="work/x",
        holder_ref="agent:test:case:agent-a",
        ttl_seconds=3600,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-a")
    monkeypatch.setattr(lanes, "delete_lease", lambda *args, **kwargs: {"ok": True})
    assert (
        lanes.retire_landed_work_lanes(
            root=tmp_path,
            branch="work/x",
            expect_head="h2",
            apply=True,
        )["state"]
        == "retired"
    )
    assert ("update-ref", "-d", "refs/heads/work/x", "h2") in calls


def test_shadow_process_json_backend_and_semantic_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert shadow_execution.parse_json_from_stdout('noise {"ok": true} tail') == {"ok": True}
    assert shadow_execution.parse_json_from_stdout("[1,2]") == {}
    assert shadow_execution.parse_json_from_stdout("{bad") == {}
    assert shadow_execution.process_failed({"exit_code": 124, "json": {}}) is True
    assert shadow_execution.process_failed({"exit_code": 0, "json": {"ok": True}}) is True
    verdict = {"ok": False, "command": "land", "required_gaps": []}
    assert shadow_execution.process_failed({"exit_code": 1, "json": verdict}) is False
    assert shadow_execution.process_failed({"exit_code": 2, "json": verdict}) is True

    class TimeoutRun:
        def __call__(self, *args: object, **kwargs: object) -> object:
            raise subprocess.TimeoutExpired(cmd=["x"], timeout=1, output="out", stderr="err")

    monkeypatch.setattr(shadow_execution.subprocess, "run", TimeoutRun())
    assert (
        shadow_execution.run_json_command(["x"], cwd=tmp_path, timeout_seconds=1)["exit_code"]
        == 124
    )
    monkeypatch.setattr(
        shadow_execution.subprocess,
        "run",
        lambda *args, **kwargs: cp(
            stdout='prefix {"ok":true,"command":"status","required_gaps":[]} suffix'
        ),
    )
    assert (
        shadow_execution.run_json_command(["x"], cwd=tmp_path, timeout_seconds=1)["json"]["command"]
        == "status"
    )

    assert shadow_execution.embedded_backend(tmp_path, ("status",))["kind"] == "missing"
    (tmp_path / "pixi.toml").write_text("[workspace]\n", encoding="utf-8")
    assert shadow_execution.embedded_backend(tmp_path, ("status",))["kind"] == "pixi"
    (tmp_path / "pixi.toml").unlink()
    (tmp_path / "pyproject.toml").write_text("[tool.uv.workspace]\nmembers=[]\n", encoding="utf-8")
    assert shadow_execution.embedded_ethos_command(tmp_path, ("status",))[0] == "uv"
    (tmp_path / "pyproject.toml").write_text("[bad\n", encoding="utf-8")
    assert shadow_execution.pyproject_tool(tmp_path) == {}

    for command, payload, expected_key in [
        (
            ("status",),
            {
                "ok": True,
                "command": "status",
                "data": {"role": "work_lane", "changed_paths": ["a"], "dirty": True},
                "required_gaps": [],
            },
            "changed_path_count",
        ),
        (
            ("plan", "--changed"),
            {
                "ok": True,
                "data": {
                    "required_gates": [{"id": "g"}],
                    "matched_rules": [{"id": "r"}],
                },
                "required_gaps": [],
            },
            "required_gate_ids",
        ),
        (
            ("prove",),
            {"ok": True, "state": "ready", "required_gaps": []},
            "proof_ready",
        ),
        (
            ("quality", "command-surface"),
            {
                "ok": True,
                "summary": {"retired_violation_count": 2},
                "required_gaps": [],
            },
            "retired_violation_count",
        ),
        (
            ("assistants", "doctor"),
            {"ok": True, "required_gaps": []},
            "assistant_ready",
        ),
        (
            ("playbooks", "route", "--changed"),
            {"ok": True, "required_gaps": []},
            "route_ready",
        ),
        (
            ("land",),
            {"ok": True, "data": {"remote_push": "deferred"}, "required_gaps": []},
            "readiness",
        ),
        (
            ("publish",),
            {"ok": True, "summary": {"remote_push": "ready"}, "required_gaps": []},
            "remote_push",
        ),
    ]:
        assert expected_key in shadow_semantics._semantic_projection(command, payload)  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch

    external = {
        "ok": False,
        "command": "report",
        "state": "gapped",
        "summary": {"parity_pending_count": 3, "governance_gap_count": 0},
        "required_gaps": [],
    }
    embedded = {
        "ok": True,
        "command": "report",
        "state": "ready",
        "summary": {},
        "required_gaps": [],
    }
    assert (
        shadow_semantics.accepted_semantic_differences(("report",), external, embedded)[0]["kind"]
        == "report_parity_evidence_refresh_bootstrap"
    )
    route_external = {
        "command": "playbooks route",
        "data": {"command": "playbooks route", "subject": "changed-scope"},
        "required_gaps": ["skill_missing_id"],
    }
    route_embedded = {
        "summary": {"changed_requested": True, "changed_path_count": 0},
        "required_gaps": [],
    }
    filtered, removed = shadow_semantics._without_changed_route_noop_gaps(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        route_external, route_embedded, ["skill_missing_id"]
    )
    assert filtered == [] and removed == ["skill_missing_id"]


def test_parity_evidence_validation_edges(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence" / "parity"
    evidence_dir.mkdir(parents=True)
    path = evidence_dir / "generic-shadow.json"
    path.write_text("[]", encoding="utf-8")
    assert parity.parity_gaps_report(adopter="generic", root=tmp_path)["evidence"][
        "required_gaps"
    ] == ["parity_evidence_not_object"]

    target = tmp_path / "target"
    target.mkdir()
    payload = parity.build_tracked_parity_evidence(
        adopter="generic",
        target=target,
        shadow={"ok": True, "required_gaps": [], "accepted_summary": {}},
        current_product_head="p1",
        current_target_head="t1",
        timeout_seconds=30,
    )
    payload["verified_capabilities"] = ["not-a-capability"]
    payload["capability_basis"] = {}
    path.write_text(json.dumps(payload), encoding="utf-8")
    gaps = parity.parity_gaps_report(
        adopter="generic",
        root=tmp_path,
        target=target,
        current_product_head="p1",
        current_target_head="t1",
    )["evidence"]["required_gaps"]
    assert "parity_evidence_invalid:generic:unknown_capability" in gaps

    payload = parity.build_tracked_parity_evidence(
        adopter="generic",
        target=target,
        shadow={"ok": True, "required_gaps": [], "accepted_summary": {}},
        current_product_head="p1",
        current_target_head="t1",
        timeout_seconds=30,
    )
    payload["freshness"] = {
        "product_head": "p1",
        "target_head": "t1",
        "command_sha256": "bad",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert (
        "parity_evidence_invalid:generic:command_sha256"
        in parity.parity_gaps_report(adopter="generic", root=tmp_path, target=target)["evidence"][
            "required_gaps"
        ]
    )


def test_retrieval_index_search_verify_and_purge_edges(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# ETHOS\n\nhello retrieval\n", encoding="utf-8")
    py = tmp_path / "packages" / "demo" / "mod.py"
    py.parent.mkdir(parents=True)
    py.write_text("def alpha():\n    return 'retrieval'\n", encoding="utf-8")
    # Patch tracked_files in sources so allowed_sources sees the stub files.
    monkeypatch.setattr(retrieval_sources, "tracked_files", lambda root: [readme, py])
    # Patch dirty_allowed_sources in both indexing (rebuild) and query (search/verify).
    monkeypatch.setattr(retrieval_indexing, "dirty_allowed_sources", lambda root: [])
    monkeypatch.setattr(retrieval_query, "dirty_allowed_sources", lambda root: [])
    # Patch git_head in both indexing (rebuild) and query (search/verify).
    monkeypatch.setattr(retrieval_indexing, "git_head", lambda root: "h1")
    monkeypatch.setattr(retrieval_query, "git_head", lambda root: "h1")
    # Patch tracked_source_paths in query (verify_candidate).
    monkeypatch.setattr(
        retrieval_query,
        "tracked_source_paths",
        lambda root: {"README.md", "packages/demo/mod.py"},
    )

    dry = retrieval_indexing.rebuild_context_index(tmp_path, apply=False, authorized=False)
    assert dry["state"] == "dry_run"
    assert retrieval_indexing.rebuild_context_index(tmp_path, apply=True, authorized=False)[
        "required_gaps"
    ] == ["context_index_requires_authorization"]
    indexed = retrieval_indexing.rebuild_context_index(tmp_path, apply=True, authorized=True)
    assert indexed["state"] == "indexed"

    found = retrieval_query.search_context_index(tmp_path, "retrieval", limit=5)
    assert found["ok"] is True
    assert found["summary"]["verified_count"] >= 1
    assert (
        retrieval_query.query_candidates(
            retrieval_common.default_retrieval_db_path(tmp_path), "!!!", limit=3
        )
        == []
    )

    stale_candidate = dict(
        retrieval_query.query_candidates(
            retrieval_common.default_retrieval_db_path(tmp_path), "ETHOS", limit=1
        )[0]
    )
    stale_candidate["head"] = "old"
    assert (
        retrieval_query.verify_candidate(tmp_path, stale_candidate)["verification"]["reason"]
        == "head_mismatch"
    )
    outside_candidate = dict(stale_candidate, path="../outside.md", head="h1")
    assert (
        retrieval_query.verify_candidate(tmp_path, outside_candidate)["verification"]["reason"]
        == "path_outside_repository"
    )
    missing_candidate = dict(stale_candidate, path="docs/missing.md", head="h1")
    monkeypatch.setattr(retrieval_query, "tracked_source_paths", lambda root: {"docs/missing.md"})
    monkeypatch.setattr(
        retrieval_query,
        "allowed_sources",
        lambda root: [tmp_path / "docs" / "missing.md"],
    )
    assert (
        retrieval_query.verify_candidate(tmp_path, missing_candidate)["verification"]["reason"]
        == "missing_path"
    )

    db_path = retrieval_common.default_retrieval_db_path(tmp_path)
    (db_path.with_suffix(".sqlite-wal")).write_text("wal", encoding="utf-8")
    assert (
        retrieval_indexing.purge_context_index(tmp_path, apply=False, authorized=False)["state"]
        == "dry_run"
    )
    assert retrieval_indexing.purge_context_index(tmp_path, apply=True, authorized=False)[
        "required_gaps"
    ] == ["context_purge_requires_authorization"]
    purged = retrieval_indexing.purge_context_index(tmp_path, apply=True, authorized=True)
    assert "retrieval.sqlite" in purged["summary"]["removed"]


def test_retrieval_secret_tombstone_and_dirty_search(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret = tmp_path / "README.md"
    secret.write_text("OPENAI_API_KEY=sk-" + "x" * 40, encoding="utf-8")
    db = tmp_path / ".ethos" / "state" / "retrieval.sqlite"
    from ethos.adapters.store.retrieval.schema import initialize_context_index

    initialize_context_index(db)
    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "insert into index_manifests(id, root, head, schema_version, policy_digest, created_at, payload_json) values (?, ?, ?, ?, ?, ?, ?)",
            ("m1", tmp_path.as_posix(), "h1", 1, "p", "now", "{}"),
        )
        counts = retrieval_indexing.index_source(connection, tmp_path, "m1", secret, "h1")
        tombstone_count = connection.execute("select count(*) from tombstones").fetchone()[0]
    assert counts["chunk_count"] == 0
    assert tombstone_count == 1

    monkeypatch.setattr(retrieval_query, "dirty_allowed_sources", lambda root: ["README.md"])
    assert retrieval_query.search_context_index(tmp_path, "x")["required_gaps"] == [
        "context_index_dirty_sources"
    ]
