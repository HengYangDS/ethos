"""Proof consumption binds exact live intent, evidence applicability and effect authority."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.proof as proof_module
import ethos.adapters.mutation.proof_admission as proof_admission
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.value import frozen_tuple
from ethos.contracts.value import mutable_json
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.literal_cases import literal_case
from tests.support.proof import assert_selected_proof
from tests.support.proof import current_proof_plan
from tests.support.proof import issue_conformant_proof
from tests.support.proof import proof_repository
from tests.support.proof import store_proof
from tests.support.semantic import commitment_fixture
from tests.support.semantic import reissue_attestation

if TYPE_CHECKING:
    from pathlib import Path

    from tests.support.governed_repository import WorkLaneFixture


_issue = partial(issue_conformant_proof, issuer="agent:test:case:proof")


@pytest.mark.parametrize(
    ("case", "gap"),
    frozen_tuple(
        literal_case(
            "kernel.test_proof_admission:parametrize:test_proof_admission_rechecks_live_plan_closure:1"
        )
    ),
)
def test_proof_admission_rechecks_live_plan_closure(tmp_path: Path, case: str, gap: str) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    valid = _issue(repo, head)
    plan = current_proof_plan(repo, expected_head=head)
    facts = Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC)})
    if case in {"head", "tree"}:
        facts = facts.model_copy(update={case: "0" * 40})
    policy = dict(plan.policy) | ({"noncanonical": True} if case == "policy" else {})
    forged = compile_plan(
        Commitment.model_validate(dict(plan.commitment)),
        facts,
        plan.nodes,
        policy=policy,
        prior_attestations=dict(plan.prior_attestations),
    )
    if case == "policy":
        with pytest.raises(ValueError, match="proof_plan_binding_mismatch"):
            _issue(repo, head, plan=forged)
    store_proof(
        repo,
        reissue_attestation(
            valid,
            commitment_digest=forged.inputs.commitment,
            facts_digest=forged.inputs.facts,
            plan_digest=forged.digest,
            policy_digest=forged.inputs.policy,
            effect_digest=forged.inputs.effect,
            body=valid.payload.body | {"plan": forged.model_dump(mode="json")},
        ),
    )
    assert_selected_proof(repo, head, gap=gap)


@pytest.mark.parametrize("omit", [False, True])
def test_repository_transition_rejects_acceptance_not_bound_to_source(tmp_path, omit):
    """Correct object hashes and green checks cannot validate invented intent."""
    fixture = start_adopted_work_lane(tmp_path)
    head = git(fixture.worktree, "rev-parse", "HEAD")
    source = current_proof_plan(fixture.worktree, expected_head=head)
    forged = compile_plan(
        None if omit else commitment_fixture(id="change:fixture-change"),
        Facts.model_validate(dict(source.facts) | {"observed_at": datetime.now(UTC)}),
        source.nodes,
        policy=dict(source.policy),
    )
    record = _issue(fixture.worktree, head, plan=forged)
    persist_proof_attestation(fixture.worktree, record)

    selected, gaps = proof_module.proof_for_repository_transition(fixture.worktree, head)

    assert selected is None
    assert gaps == ["proof_source_intent_mismatch"]


def _archive_bound_work_proof(
    tmp_path: Path, *, omit: bool = False
) -> tuple[WorkLaneFixture, str, Attestation]:
    """Produce actual archive evidence rather than a synthetic archive-shaped claim."""
    fixture = start_adopted_work_lane(tmp_path)
    head = commit_fixture_file(
        fixture.worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete source work",
    )
    persist_proof_attestation(fixture.worktree, _issue(fixture.worktree, head))
    run_ethos(
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=fixture.worktree,
    )
    head = git(fixture.worktree, "rev-parse", "HEAD")
    source = current_proof_plan(fixture.worktree, expected_head=head)
    plan = (
        compile_plan(
            None,
            Facts.model_validate(dict(source.facts) | {"observed_at": datetime.now(UTC)}),
            source.nodes,
            policy=dict(source.policy),
            prior_attestations=mutable_json(source.prior_attestations),
        )
        if omit
        else source
    )
    proof = _issue(fixture.worktree, head, plan=plan)
    persist_proof_attestation(fixture.worktree, proof)
    git(fixture.candidate, "reset", "--hard", head)
    return fixture, head, proof


def test_repository_transition_uses_archive_proof_after_lease_retirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, head, proof = _archive_bound_work_proof(tmp_path)
    monkeypatch.setattr(proof_admission, "leases_by_branch", lambda _root: {})
    selected, gaps = proof_module.proof_for_repository_transition(fixture.candidate, head)
    assert selected == proof
    assert gaps == []


def test_repository_transition_rejects_omitted_archived_intent(tmp_path: Path) -> None:
    """Archive absence is not permission to discard accepted source meaning."""
    fixture, head, _proof = _archive_bound_work_proof(tmp_path, omit=True)

    selected, gaps = proof_module.proof_for_repository_transition(fixture.candidate, head)

    assert selected is None
    assert gaps == ["proof_source_intent_mismatch"]


def test_repository_transition_accepts_exact_active_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pending delivery does not invalidate proved source acceptance."""
    fixture = start_adopted_work_lane(tmp_path)
    head = commit_fixture_file(fixture.worktree, "FEATURE.md", "feature\n", "feature")
    proof = _issue(fixture.worktree, head)
    persist_proof_attestation(fixture.worktree, proof)
    git(fixture.candidate, "reset", "--hard", head)
    monkeypatch.setattr(proof_admission, "leases_by_branch", lambda _root: {})

    selected, gaps = proof_module.proof_for_repository_transition(fixture.candidate, head)

    assert selected == proof
    assert gaps == []


def test_repository_transition_rejects_conflicting_archive_proofs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, head, proof = _archive_bound_work_proof(tmp_path)
    monkeypatch.setattr(proof_admission, "leases_by_branch", lambda _root: {})
    persist_proof_attestation(
        fixture.candidate,
        reissue_attestation(
            proof,
            verifier="agent:test:case:conflict",
            body=proof.payload.body | {"claim": {"objective": "conflict", "verdict": "pass"}},
        ),
    )

    selected, gaps = proof_module.proof_for_repository_transition(fixture.candidate, head)

    assert selected is None
    assert gaps == ["contradiction"]


def test_equivalent_proofs_supersede_deterministically_but_conflicts_block(tmp_path: Path) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    first = _issue(repo, head)
    persist_proof_attestation(repo, first)
    later = reissue_attestation(first, issued_at=first.issued_at + timedelta(seconds=1))
    persist_proof_attestation(repo, later)
    assert_selected_proof(repo, head, selected=min((first, later), key=lambda record: record.id))
    conflict = reissue_attestation(
        first,
        verifier="agent:test:case:conflict",
        body=first.payload.body | {"claim": {"objective": "conflict", "verdict": "pass"}},
    )
    persist_proof_attestation(repo, conflict)
    assert_selected_proof(repo, head, gap="contradiction")


@pytest.mark.parametrize("novel", [False, True])
def test_expired_or_other_query_proofs_do_not_pollute_current_authority(
    tmp_path: Path, *, novel: bool
) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    current = _issue(repo, head)
    persist_proof_attestation(repo, current)
    issued = datetime.now(UTC) - timedelta(minutes=2)
    store_proof(
        repo,
        reissue_attestation(
            current,
            issued_at=issued,
            valid_from=issued,
            valid_until=issued + timedelta(minutes=1),
            **({"body": current.payload.body | {"novel_semantics": True}} if novel else {}),
        ),
    )
    assert_selected_proof(repo, head, selected=current)
    store_proof(
        repo, reissue_attestation(current, body=current.payload.body | {"scope": ("workspace",)})
    )
    assert_selected_proof(repo, head, selected=current)


@pytest.mark.parametrize("gap", ["git_common_directory_unavailable", "artifact_store_unreadable"])
def test_proof_gaps_preserves_nonrepository_and_store_failure_distinction(
    tmp_path, monkeypatch, gap
):
    def unavailable(_root):
        raise ValueError(gap)

    if gap == "git_common_directory_unavailable":
        assert proof_gaps(tmp_path, "a" * 40) == ["attestation_set_repository_invalid"]
    else:
        monkeypatch.setattr(proof_module, "proof_artifact_root", unavailable)
        with pytest.raises(ValueError, match=gap):
            proof_gaps(tmp_path, "a" * 40)
