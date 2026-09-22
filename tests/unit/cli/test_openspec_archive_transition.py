"""Verify exact native archive effects, derived bindings and recovery boundaries."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.archive.effect as archive_effect
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.lifecycle.archive_transition import ArchivePostimage
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage_scope_report
from ethos.adapters.repo.worktree_postimage import observe_worktree_postimage
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.openspec_lifecycle import assert_lifecycle_outcome
from tests.support.openspec_lifecycle import completed_lifecycle
from tests.support.proof import seed_executed_proof
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

    from tests.support.openspec_lifecycle import OpenSpecLifecycle


@pytest.fixture(autouse=True)
def _avoid_unrelated_runtime_materialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep archive tests on lifecycle semantics, not self-host runtime setup."""
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.start.install_hook_launchers",
        lambda _root: {},
    )


def test_public_prewrite_repairs_canonical_output_after_native_archive(monkeypatch, tmp_path):
    """An archived Change remains a repair source, not reusable write permission."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    root = lifecycle.worktree
    delta = lifecycle.active / "specs/contracts/spec.md"
    new_delta = lifecycle.active / "specs/new-capability/spec.md"
    new_delta.parent.mkdir()
    delta.rename(new_delta)
    commit_fixture(root, "declare a new canonical capability")
    monkeypatch.setattr(archive, "proof_gaps", proof_gaps)
    seed_executed_proof(root, lifecycle.head)
    archived = lifecycle.apply_archive()
    assert archived["state"] == "repair_required"
    assert archived["effect_state"] == "committed"
    path = "openspec/specs/new-capability/spec.md"
    assert "TBD" in (root / path).read_text(encoding="utf-8")
    assert not lifecycle.active.exists()
    arguments = (path, "--editor-root", str(root), "--require-editor-root", "--json")
    for command in (("lane", "prewrite"), ("hook", "admit", "pre-tool")):
        result = run_ethos(*command, *arguments, cwd=root)
        assert result["verdict"] == "pass", result
        admission = result["data"] if command[0] == "lane" else result["data"]["admission"]
        assert admission["material_scope"]["authorized_paths"] == [path]
    mixed = run_ethos_blocked("lane", "prewrite", "README.md", *arguments, cwd=root)
    assert mixed["verdict"] == "block"
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    stale = run_ethos_blocked("lane", "prewrite", *arguments, cwd=root)
    assert any("lease_holder_mismatch" in gap for gap in stale["required_gaps"])
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    canonical = root / path
    canonical.write_text(
        canonical.read_text(encoding="utf-8").replace(
            "TBD - created by archiving change fixture-change. Update Purpose after archive.",
            "Exercise a newly archived capability through exact canonical repair admission.",
        ),
        encoding="utf-8",
    )
    assert "TBD" not in canonical.read_text(encoding="utf-8")
    commit_fixture(root, "repair canonical purpose")
    repaired = run_ethos("lane", "prewrite", *arguments, cwd=root)
    assert repaired["verdict"] == "pass"
    assert repaired["data"]["material_scope"]["state"] == "archive_attested"


def _stage_exact_archive(lifecycle: OpenSpecLifecycle) -> str:
    archive_path = "openspec/changes/archive/2026-08-04-fixture-change"
    target = lifecycle.worktree / archive_path
    target.parent.mkdir(parents=True, exist_ok=True)
    lifecycle.active.rename(target)
    git(lifecycle.worktree, "add", "--all")
    return archive_path


def _staged_postimage(root: Path, *, head: str, change: str) -> ArchivePostimage:
    with observe_worktree_postimage(root, previous=head) as observed:
        archive_root = next(
            path.rsplit("/", 1)[0]
            for path in observed.changed_paths
            if path.startswith("openspec/changes/archive/") and path.endswith("/proposal.md")
        )
        return ArchivePostimage(
            change=change,
            head=head,
            scope={
                "archive_path": archive_root,
                "changed_paths": observed.changed_paths,
                "tree": observed.tree,
            },
            active_present=False,
        )


def _compiled_archive_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[OpenSpecLifecycle, TransitionPlan, str, str]:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    archive_path = _stage_exact_archive(lifecycle)
    tree = git(lifecycle.worktree, "write-tree")
    target = git(
        lifecycle.worktree,
        "commit-tree",
        tree,
        "-p",
        lifecycle.completed_head,
        "-m",
        "chore(openspec): archive fixture-change",
    )
    monkeypatch.setattr(
        archive_effect,
        "archive_postimage_scope_report",
        lambda *_args, **_kwargs: {"verdict": "pass", "archive_path": archive_path},
    )
    commitment = commitment_fixture(id="change:fixture-change")
    monkeypatch.setattr(
        archive_effect,
        "load_profile_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("archive plan must consume the resolved Commitment")
        ),
        raising=False,
    )
    plan = archive_effect.compile_archive_plan(
        lifecycle.worktree,
        lifecycle.branch,
        "fixture-change",
        lifecycle.completed_head,
        target,
        lifecycle.lease,
        commitment=commitment,
    )
    return lifecycle, plan, target, archive_path


def test_archive_plan_is_one_common_git_ref_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle, plan, target, archive_path = _compiled_archive_plan(tmp_path, monkeypatch)

    assert plan.policy["operation"] == "git.ref.compare-and-swap"
    assert plan.policy["transition"] == "openspec.archive"
    assert plan.policy["branch"] == lifecycle.branch
    update = git_effect_from_plan(plan).updates[f"refs/heads/{lifecycle.branch}"]
    assert (update.expected, update.desired) == (lifecycle.completed_head, target)
    values = plan.facts["values"]
    assert isinstance(values, Mapping)
    assert values["archive_path"] == archive_path


def test_archive_executor_replay_recognizes_the_durable_effect_without_reexecution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle, plan, target, archive_path = _compiled_archive_plan(tmp_path, monkeypatch)
    issued = archive_effect.execute_git_effect(
        lifecycle.worktree,
        plan,
        issuer=str(lifecycle.lease["holder_ref"]),
    )
    assert issued.predicate == "effect:git-ref-update"
    assert git(lifecycle.worktree, "rev-parse", "HEAD") == target

    monkeypatch.setattr(
        archive_effect, "execute_git_effect", lambda *_a, **_k: pytest.fail("replayed Git effect")
    )

    recovered, replayed = [
        archive_effect.complete_archive(
            lifecycle.worktree, lifecycle.branch, "fixture-change", plan, target, apply=True
        )
        for _ in range(2)
    ]

    assert (recovered["state"], replayed["state"]) == ("recognized", "recognized")
    assert (recovered["attestation"], replayed["attestation"]) == (
        issued.model_dump(mode="json"),
    ) * 2
    assert recovered["archive_path"] == archive_path
    assert (replayed["lease"], recovered["lease"]) == (lifecycle.lease,) * 2


def test_archive_common_effect_rejects_cas_drift_before_mutation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle, plan, target, _archive_path = _compiled_archive_plan(tmp_path, monkeypatch)
    drift = git(
        lifecycle.worktree,
        "commit-tree",
        "HEAD^{tree}",
        "-p",
        lifecycle.completed_head,
        "-m",
        "drift",
    )
    git(
        lifecycle.worktree,
        "update-ref",
        f"refs/heads/{lifecycle.branch}",
        drift,
        lifecycle.completed_head,
    )

    with pytest.raises(ValueError, match=r"git_effect_(plan_prestate_stale|cas_mismatch)"):
        archive_effect.execute_git_effect(
            lifecycle.worktree,
            plan,
            issuer=str(lifecycle.lease["holder_ref"]),
        )

    assert git(lifecycle.worktree, "rev-parse", lifecycle.branch) == drift
    assert git(lifecycle.worktree, "rev-parse", lifecycle.branch) != target


def _declare_archive_binding(root: Path) -> tuple[str, Path, dict[str, object]]:
    """Bind an authored graph to a real canonical spec for archive scenarios."""
    source = "openspec/specs/contracts/spec.md"
    projection = root / "system/projections/terminal-architecture"
    projection.mkdir(parents=True)
    active = root / "openspec/changes/fixture-change"
    target = root / "docs/reference.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text("# Reference\n")
    (active / "design.md").write_text("[Reference](../../../docs/reference.md)\n")
    delta = active / "specs/contracts/spec.md"
    delta.write_text(
        delta.read_text().replace(
            "single intent carrier.", "[reference](../../../../../docs/reference.md)."
        )
    )
    binding = {
        "path": source,
        "authority": "fixture canonical contract",
        "sha256": hashlib.sha256((root / source).read_bytes()).hexdigest(),
    }
    graph = {"sources": {"contract": binding}, "nodes": {"intent": {"label": "Keep meaning"}}}
    graph_path = projection / "semantic-graph.json"
    for path, content in {
        graph_path: graph,
        projection / "declaration.json": {
            "schema": "ethos.projection-declaration/v1",
            "sources": [{"id": "contract", **{k: binding[k] for k in ("path", "authority")}}],
            "documents": {"semantic_graph": graph_path.relative_to(root).as_posix()},
        },
    }.items():
        path.write_text(json.dumps(content) + "\n", encoding="utf-8")
    commit_fixture(root, "declare bound projection")
    return source, graph_path, graph


def _inject_archive_failure(monkeypatch, mode, root, head):
    """Inject failure at its actual observation or Git-commit boundary."""
    if mode == "observation-failure":
        monkeypatch.setattr(
            archive,
            "archive_postimage",
            Mock(
                side_effect=[
                    archive.archive_postimage(root, head=head, change="fixture-change"),
                    ValueError("archive_reference_observation_timeout"),
                ]
            ),
        )
    elif mode.endswith("failure"):
        monkeypatch.setattr(
            archive_effect,
            "create_git_commit",
            lambda *_args, **_kwargs: Mock(returncode=1, stdout="", stderr="commit refused"),
        )


def _assert_archive_rejects_changed_meaning(root, graph_path, graph, source_head, current_head):
    """A derived binding cannot authorize changed authored graph meaning."""
    graph_path.write_text(json.dumps({**graph, "nodes": {}}) + "\n", encoding="utf-8")
    with observe_worktree_postimage(root, previous=source_head) as postimage:
        rejected = archive_postimage_scope_report(
            root,
            source_head=source_head,
            tree=postimage.tree,
            changed_paths=postimage.changed_paths,
            requested_change="fixture-change",
            environment=postimage.environment,
        )
    assert rejected is None
    assert git(root, "rev-parse", "HEAD") == current_head


@pytest.mark.parametrize(
    "mode",
    [
        "native",
        "staged",
        "native-failure",
        "staged-failure",
        "staged-index-failure",
        "observation-failure",
    ],
)
def test_official_archive_closes_its_exact_source_binding_projection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str
) -> None:
    """Archival must not strand a proven Change behind stale derived hashes."""
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    root = lifecycle.worktree
    source, graph_path, graph = _declare_archive_binding(root)
    head = lifecycle.head
    monkeypatch.setattr(archive, "proof_gaps", proof_gaps)
    monkeypatch.setattr(archive_effect, "proof_gaps", proof_gaps)
    seed_executed_proof(root, head)
    if mode.startswith("staged"):
        staged_archive = lifecycle.stage_official_archive()
        if mode == "staged-index-failure":
            git(root, "add", "--all")
    before_index = git(root, "write-tree")
    before_work = git(root, "status", "--porcelain")
    before_graph = graph_path.read_bytes()
    _inject_archive_failure(monkeypatch, mode, root, head)
    arguments = (
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--root",
        root.as_posix(),
        "--apply",
        "--json",
    )
    report = run_ethos_blocked(*arguments, cwd=root)["data"]

    if mode.endswith("failure"):
        assert report["required_gaps"] == [
            "archive_reference_observation_timeout"
            if mode == "observation-failure"
            else "openspec_archive_commit_failed"
        ]
        assert report["compensation_state"] == "completed"
        if mode.startswith("staged"):
            assert report["effect_state"] == "mutated"
            assert (root / staged_archive / "proposal.md").is_file()
        assert lifecycle.head == head
        assert git(root, "write-tree") == before_index
        assert git(root, "status", "--porcelain") == before_work
        assert graph_path.read_bytes() == before_graph
        return

    assert report["required_gaps"] == ["proof_not_proven"], report
    archived = root / report["archive_path"]
    assert "../../../../docs/reference.md" in (archived / "design.md").read_text()
    assert (
        "../../../../../../docs/reference.md" in (archived / "specs/contracts/spec.md").read_text()
    )
    assert "../../../docs/reference.md" in (root / source).read_text()
    digest = hashlib.sha256((root / source).read_bytes()).hexdigest()
    assert digest != graph["sources"]["contract"]["sha256"]
    graph["sources"]["contract"]["sha256"] = digest
    assert json.loads(graph_path.read_bytes()) == graph
    assert graph_path.relative_to(root).as_posix() in report["changed_paths"]
    assert git(root, "status", "--short") == ""
    archived_head = lifecycle.head
    assert f"--expect-head {archived_head}" in report["next_action"]
    assert git(root, "rev-parse", "HEAD^") == head
    seed_executed_proof(root, archived_head)
    assert proof_gaps(root, archived_head) == []
    replay = run_ethos(*arguments, cwd=root)
    assert replay["data"]["state"] == "recognized"
    assert replay["data"]["attestation"] == report["attestation"]

    _assert_archive_rejects_changed_meaning(root, graph_path, graph, head, archived_head)


def test_archive_change_blocks_when_the_work_lane_lease_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    with closing(sqlite3.connect(state_database(lifecycle.worktree))) as connection, connection:
        connection.execute("delete from leases where lane_ref = ?", (lifecycle.branch,))

    report = archive.archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
        apply=True,
    )

    assert report["state"] == "lease_missing"
    assert report["required_gaps"] == [f"work_lane_missing_lease:{lifecycle.branch}"]
    assert_lifecycle_outcome(
        report,
        "zero_effect",
        "not_required",
        "absent",
        f"ethos lane lease reacquire --path {lifecycle.worktree.resolve().as_posix()} "
        "--holder-ref agent:test:case:agent-test "
        f"--root {lifecycle.worktree.resolve().as_posix()} --json",
        user_decision_required=True,
    )
    assert lifecycle.head == lifecycle.completed_head
    assert lifecycle.active.is_dir()


def test_staged_archive_recovery_resolves_intent_from_the_exact_source_head(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lifecycle = completed_lifecycle(tmp_path, monkeypatch)
    _stage_exact_archive(lifecycle)
    monkeypatch.setattr(archive, "archive_postimage", _staged_postimage)
    resolve = Mock(wraps=archive.resolve_current_resolution)
    monkeypatch.setattr(archive, "resolve_current_resolution", resolve)

    report = archive.archive_change(
        root=lifecycle.worktree,
        change="fixture-change",
        expect_head=lifecycle.completed_head,
    )

    assert report["state"] == "ready_to_finalize_archive"
    assert resolve.call_count == 1
    assert resolve.call_args.kwargs["intent_tree_ref"] == lifecycle.completed_head
