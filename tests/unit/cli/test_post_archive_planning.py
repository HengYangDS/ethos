from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.archive_change import archive_change
from ethos.adapters.mutation.lane_lifecycle.change_rollover import start_change
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.surface.cli.root.proof import _generation_scope
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_plan_admits_the_exact_post_archive_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(
        tmp_path,
        scope=("openspec/changes/fixture-change/**",),
    )
    worktree = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "complete fixture change")
    completed = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=completed,
    )
    assert advanced["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    archived = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed,
        apply=True,
    )
    assert archived["verdict"] == "pass", archived

    payload = run_ethos("plan", "--changed", "--root", worktree.as_posix(), "--json", cwd=worktree)

    assert payload["verdict"] == "pass", payload
    authority = payload["data"]["transition_plan"]["prior_attestations"]["openspec_archive"]
    assert authority["predicate"] == "effect:openspec-archive"


def test_plan_and_prove_bind_only_the_current_post_start_generation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(tmp_path, scope=("openspec/changes/fixture-change/**",))
    worktree = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    previous = git(worktree, "rev-parse", "HEAD")
    tasks = worktree / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ]", "- [x]"))
    git(worktree, "add", tasks.relative_to(worktree).as_posix())
    git(worktree, "commit", "-m", "complete fixture change")
    completed = git(worktree, "rev-parse", "HEAD")
    advanced = work_lane_ref_transition_report(
        root=worktree,
        phase="committed",
        ref_name=f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        old_value=previous,
        new_value=completed,
    )
    assert advanced["state"] == "lease_ref_advanced"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_lifecycle.archive_change.proof_gaps",
        lambda _root, _head: [],
    )
    archived = archive_change(
        root=worktree,
        change="fixture-change",
        expect_head=completed,
        apply=True,
    )
    assert archived["verdict"] == "pass", archived
    overlay = worktree / "README.md"
    overlay.write_text("forward fix\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    started = start_change(
        root=worktree,
        change="hosted-verification-fix",
        intent="Repair the current generation without reopening archived work.",
        scope=("README.md",),
        expect_head=git(worktree, "rev-parse", "HEAD"),
        expected_overlay_digest=dirty_content_sha256(worktree),
        apply=True,
    )
    assert started["verdict"] == "pass", started
    overlay.write_text("forward fix, dirty now\n", encoding="utf-8")
    expected = {
        "README.md",
        "openspec/changes/hosted-verification-fix/.openspec.yaml",
        "openspec/changes/hosted-verification-fix/commitment.toml",
    }
    plan_payload = run_ethos(
        "plan", "--changed", "--root", worktree.as_posix(), "--json", cwd=worktree
    )
    assert plan_payload["verdict"] == "block", plan_payload
    assert "change_scope_exceeded" not in plan_payload["required_gaps"], plan_payload
    assert not any("archive/" in gap for gap in plan_payload["required_gaps"]), plan_payload
    assert set(plan_payload["data"]["changed_paths"]) == expected
    plan = plan_payload["data"]["transition_plan"]
    assert set(plan["facts"]["values"]["changed_paths"]) == expected
    prior = plan["prior_attestations"]
    assert prior["openspec_change_start"]["predicate"] == "effect:openspec-change-start"

    scope = _generation_scope(worktree)
    proof = proof_plan(
        worktree,
        head=git(worktree, "rev-parse", "HEAD"),
        gate_ids=("sample-tests",),
        changed_paths=scope.paths,
        generation_scope=scope,
    )
    assert set(proof.facts["values"]["changed_paths"]) == expected
    assert proof.prior_attestations["openspec_change_start"]["predicate"] == (
        "effect:openspec-change-start"
    )
