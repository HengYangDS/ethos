"""Reverse candidate CAS requires the prior destination's own fresh proof."""

from __future__ import annotations

import json
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.landing as landing
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.repo.worktree_effects import sync_worktree
from ethos.contracts.branch.roles import load_branch_role_policy
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.unit.land.source_acceptance.support import prepare_source
from tests.unit.land.source_acceptance.support import prove_source

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan


@pytest.mark.parametrize("reject_inverse", [False, True], ids=["reverse", "preserve-recovery"])
def test_local_source_candidate_compensation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    audit_attempts: list[str],
    *,
    reject_inverse: bool,
) -> None:
    """A -> B -> A uses real hooks; refusal preserves B and its recoverable intent."""
    actor = "agent:test:case:agent-test"
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.delenv("CI", raising=False)
    fixture, accepted, previous = prepare_source(tmp_path, actor)
    work = fixture.worktree
    roles = load_branch_role_policy(work)
    ref = f"refs/heads/{roles.candidate_branch}"
    first = prove_source(work, previous, audit_attempts)
    args = ("land", "--apply", "--authorize", "--acceptance-purpose", "local-source", "--json")
    assert run_ethos(*args, "--expect-head", previous, cwd=work)["verdict"] == "pass"
    desired = commit_fixture_file(
        work, "README.md", "# Next source candidate\n", "test: next source"
    )
    second = prove_source(work, desired, audit_attempts)
    assert first.id != second.id
    forward = roles.candidate_effect(
        branch=roles.work_branch("source"), current_head=desired, candidate_head=previous
    )
    programs = []
    plans: list[TransitionPlan] = []
    native_git, observe = git_effects.run_git, git_effects.observe_git_effect
    failed = False

    def run(root, *arguments, **options):
        if arguments[:2] == ("update-ref", "--stdin"):
            programs.append(options["stdin"])
            if reject_inverse and len(programs) == 2:
                return CompletedProcess(arguments, 1, b"", b"inverse rejected")
        return native_git(root, *arguments, **options)

    def fail_after_cas(root, effect, **options):
        nonlocal failed
        observed = observe(root, effect, **options)
        if not failed and effect == forward and observed["refs"] == {ref: desired}:
            failed = True
            return {**observed, "refs": {ref: previous}}
        return observed

    def capture_plan(root, plan, **options):
        plans.append(plan)
        return git_effects.execute_git_effect(root, plan, **options)

    with monkeypatch.context() as failing:
        failing.setattr(landing, "execute_git_effect", capture_plan)
        failing.setattr(git_effects, "run_git", run)
        failing.setattr(git_effects, "observe_git_effect", fail_after_cas)
        blocked = run_ethos_blocked(*args, "--expect-head", desired, cwd=work)
    assert blocked["verdict"] == "block"
    assert programs[0] == forward.program()
    assert len(programs) == 2
    assert tuple(
        git(work, "rev-parse", branch) for branch in (roles.accepted_branch, roles.release_branch)
    ) == (accepted, accepted)
    intents = list(ref_intent_dir(work).glob("*.json"))
    if reject_inverse:
        assert git(work, "rev-parse", ref) == desired
        assert len(intents) == 1
        assert json.loads(intents[0].read_text())["phase"] == "committed"
        _recover_original_plan(
            work,
            fixture.candidate,
            plans,
            programs,
            run,
            monkeypatch,
            actor=actor,
            previous=previous,
            desired=desired,
        )
    else:
        assert git(work, "rev-parse", ref) == previous
        assert not intents
    assert git(work, "show", f"{desired}:README.md") == "# Next source candidate"
    assert len(audit_attempts) == 2


def _recover_original_plan(
    work: Path,
    candidate: Path,
    plans: list[TransitionPlan],
    programs: list,
    runner,
    monkeypatch: pytest.MonkeyPatch,
    *,
    actor: str,
    previous: str,
    desired: str,
) -> None:
    """The live caller resumes its exact transient plan; a digest is not authority."""
    assert len(plans) == 1
    with monkeypatch.context() as replay_guard:
        replay_guard.setattr(git_effects, "run_git", runner)
        recovered = git_effects.execute_git_effect(work, plans[0], issuer=actor)
    assert recovered.plan_digest == plans[0].digest
    assert len(programs) == 2
    assert not list(ref_intent_dir(work).glob("*.json"))
    sync_worktree(
        work,
        candidate,
        branch=load_branch_role_policy(work).candidate_branch,
        previous=previous,
        head=desired,
    )
    assert git(candidate, "write-tree") == git(work, "rev-parse", f"{desired}^{{tree}}")
