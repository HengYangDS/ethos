"""Proof consumption binds exact live intent, evidence applicability and effect authority."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from datetime import timedelta
from functools import partial
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.proof as proof_module
import ethos.adapters.mutation.proof_admission as proof_admission
import ethos.adapters.openspec.lifecycle.archive_transition as archive
import ethos.adapters.repo.gate_policy as gate_policy
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
from tests.support.governed_repository import prepared_work_lane
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
    fixture = prepared_work_lane(tmp_path)
    head = git(fixture.worktree, "rev-parse", "HEAD")
    source = current_proof_plan(fixture.worktree, expected_head=head)
    forged = compile_plan(
        None if omit else commitment_fixture(id="change:fixture-change"),
        Facts.model_validate(dict(source.facts) | {"observed_at": datetime.now(UTC)}),
        source.nodes,
        policy=dict(source.policy),
    )
    persist_proof_attestation(fixture.worktree, _issue(fixture.worktree, head, plan=forged))
    observed = proof_module.proof_for_repository_transition(fixture.worktree, head)
    assert observed == (None, ["proof_source_intent_mismatch"])


@pytest.mark.parametrize("archived", [False, True])
def test_repository_proof_cannot_replace_lane_generation_proof(tmp_path, monkeypatch, archived):
    """Repository evidence remains reusable without becoming authoring authority."""
    if archived:
        fixture, head, authoring = _archive_bound_work_proof(tmp_path)
    else:
        fixture = prepared_work_lane(tmp_path)
        head = git(fixture.worktree, "rev-parse", "HEAD")
        authoring = _issue(fixture.worktree, head)
    git(fixture.candidate, "reset", "--hard", head)
    record = _issue(fixture.candidate, head)
    repository_query = partial(
        proof_module.proof_for_repository_transition, fixture.candidate, head
    )
    persist_proof_attestation(fixture.candidate, record)
    if not archived:
        assert proof_gaps(fixture.worktree, head) == ["proof_lane_mismatch"]
        assert repository_query() == (record, [])
    persist_proof_attestation(fixture.worktree, authoring)
    assert proof_gaps(fixture.worktree, head) == []
    assert authoring.facts_digest != record.facts_digest
    selected = min((record, authoring), key=lambda item: item.id)
    assert repository_query() == (selected, [])
    assert repository_query(attestation_id=record.id) == (record, [])
    missing = None, ["proof_attestation_selection_missing"]
    assert repository_query(attestation_id="0" * 64) == missing
    selected_root, members = proof_admission.read_attestation_set(fixture.candidate)
    monkeypatch.setattr(
        proof_admission,
        "read_attestation_set",
        lambda _: (selected_root, tuple(item for item in members if item.id != record.id)),
    )
    assert repository_query(attestation_id=record.id) == missing


def test_proof_query_compiles_each_exact_source_policy_once(tmp_path, monkeypatch):
    """Share immutable policy work within a query, never across fresh queries."""
    repo, head = proof_repository(tmp_path / "repo")
    persist_proof_attestation(repo, _issue(repo, head))
    measured = Mock(wraps=gate_policy.load_committed_repository_profile)
    monkeypatch.setattr(gate_policy, "load_committed_repository_profile", measured)
    for attempt in range(2):
        assert proof_gaps(repo, head) == []
        assert measured.call_count == attempt + 1


def _archive_bound_work_proof(
    tmp_path: Path, *, omit: bool = False
) -> tuple[WorkLaneFixture, str, Attestation]:
    """Produce actual archive evidence rather than a synthetic archive-shaped claim."""
    fixture = prepared_work_lane(tmp_path)
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


@pytest.mark.parametrize("omit", [False, True])
def test_repository_transition_observes_one_fresh_archive_proof_set(tmp_path, monkeypatch, omit):
    """Each query uses one current set; archive withdrawal never reuses prior authority."""
    fixture, head, proof = _archive_bound_work_proof(tmp_path, omit=omit)
    monkeypatch.setattr(proof_admission, "leases_by_branch", lambda _root: {})
    observed = Mock(wraps=proof_admission.read_attestation_set)
    monkeypatch.setattr(proof_admission, "read_attestation_set", observed)
    monkeypatch.setattr(archive, "read_attestation_set", lambda _r: pytest.fail("second set read"))
    for attempt in (1, 2):
        selected, gaps = proof_module.proof_for_repository_transition(fixture.candidate, head)
        assert (selected, gaps) == (
            (None, ["proof_source_intent_mismatch"]) if omit else (proof, [])
        )
        assert observed.call_count == attempt
    observed.return_value = ("new selection", (proof,))
    selected, gaps = proof_module.proof_for_repository_transition(fixture.candidate, head)
    assert (selected == proof and not gaps) if omit else (selected is None and gaps)
    assert observed.call_count == 3


@pytest.mark.parametrize("archived", [False, True])
def test_equivalent_proofs_supersede_deterministically_but_conflicts_block(
    tmp_path, monkeypatch, archived
):
    if archived:
        fixture, head, first = _archive_bound_work_proof(tmp_path)
        repo = fixture.candidate
    else:
        repo, head = proof_repository(tmp_path / "repo")
        first = _issue(repo, head)
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change" if archived else "proof-binding")
    query = partial(
        proof_admission.proof_attestation,
        repo,
        head,
        store=proof_module.proof_artifact_root(repo),
        repository_transition=True,
    )
    persist_proof_attestation(repo, first)
    later = reissue_attestation(first, issued_at=first.issued_at + timedelta(seconds=1))
    persist_proof_attestation(repo, later)
    assert query() == (min((first, later), key=lambda record: record.id), [])
    assert proof_gaps(repo, head) == []
    monkeypatch.setenv("ETHOS_CHANGE", "missing")
    assert query()[1][0].startswith("proof_source_intent_unavailable:")
    assert query(attestation_id=first.id) == (first, [])
    exact = partial(query, attestation_id=first.id)
    assert exact(change_id="fixture-change" if archived else "proof-binding") == (first, [])
    for invalid in ("missing", ""):
        assert exact(change_id=invalid)[1][0].startswith("proof_source_intent_unavailable:")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change" if archived else "proof-binding")
    conflict = reissue_attestation(
        first,
        verifier="agent:test:case:conflict",
        body=first.payload.body | {"claim": {"objective": "conflict", "verdict": "pass"}},
    )
    persist_proof_attestation(repo, conflict)
    assert query() == (None, ["contradiction"])
    assert query(attestation_id=first.id) == (None, ["contradiction"])


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
    if gap == "git_common_directory_unavailable":
        assert proof_gaps(tmp_path, "a" * 40) == ["attestation_set_repository_invalid"]
    else:
        monkeypatch.setattr(proof_module, "proof_artifact_root", Mock(side_effect=ValueError(gap)))
        with pytest.raises(ValueError, match=gap):
            proof_gaps(tmp_path, "a" * 40)
