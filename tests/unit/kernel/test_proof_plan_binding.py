"""Exact proof semantics, current source intent and artifact-closure admission."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.proof as proof_module
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import CurrentScope
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.value import mutable_json
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_active_commitment
from tests.support.literal_cases import literal_case
from tests.support.proof import assert_selected_proof
from tests.support.proof import conformant_proof_checks
from tests.support.proof import current_proof_plan
from tests.support.proof import issue_conformant_proof
from tests.support.proof import proof_repository
from tests.support.proof import store_proof
from tests.support.semantic import commitment_fixture
from tests.support.semantic import reissue_attestation

if TYPE_CHECKING:
    from pathlib import Path


_issue = partial(issue_conformant_proof, issuer="agent:test:case:proof")


def test_proof_attestation_is_content_addressed_and_exactly_bound(tmp_path: Path) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    record = _issue(repo, head)
    selected = persist_proof_attestation(repo, record)
    assert selected["root"]
    repeated = persist_proof_attestation(repo, record)
    assert repeated["root"] == selected["root"]
    assert repeated["added"] == ()
    assert read_attestation_set(repo)[1] == (record,)
    assert record.predicate == "proof:execution"
    assert record.subject == f"git:commit:{head}"
    assert record.verdict == "pass"
    assert record.commitment_digest == plan.inputs.commitment
    assert record.facts_digest == plan.inputs.facts
    assert record.plan_digest == plan.digest
    assert record.policy_digest == plan.inputs.policy
    artifact = record.payload.body["artifact"]
    assert isinstance(artifact, Mapping)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    assert record.effect_digest == plan.inputs.effect != digest
    assert record.evidence_refs == (f"sha256:{digest}",)
    assert mutable_json(record.payload.body["plan"]) == plan.model_dump(mode="json")
    assert set(record.payload.body) == {
        "artifact",
        "boundary",
        "claim",
        "context",
        "plan",
        "plane",
        "required_gaps",
        "scope",
    }
    assert_selected_proof(repo, head, selected=record)


@pytest.mark.parametrize("with_commitment", [False, True])
def test_proof_plan_rejects_unknown_facts_without_a_commitment_bypass(
    tmp_path: Path, *, with_commitment: bool
) -> None:
    """A frozen Mapping has identical proof semantics with and without intent."""
    repo, head = proof_repository(tmp_path / "repo")
    original = current_proof_plan(repo, expected_head=head)
    facts = Facts.model_validate(
        dict(original.facts)
        | {
            "observed_at": datetime.now(UTC),
            "values": dict(original.facts["values"]) | {"unsupported_authority": True},
        }
    )
    commitment = Commitment.model_validate(dict(original.commitment)) if with_commitment else None

    with pytest.raises(ValueError, match="transition_plan_model_gap"):
        compile_plan(
            commitment,
            facts,
            original.nodes,
            policy=mutable_json(original.policy),
            prior_attestations=mutable_json(original.prior_attestations),
        )


@pytest.mark.parametrize("paths", [None, (), ("FEATURE.md",)])
def test_repository_proof_selects_only_current_archive_authority(tmp_path, paths):
    """Intent-free proof is valid; archive obligations depend on current scope."""
    _repo, candidate = start_adopted_candidate(tmp_path)
    head = git(candidate, "rev-parse", "HEAD")
    archive_authority = (
        None
        if paths is None
        else {
            "predicate": "effect:git-ref-update",
            "attestation_id": "a" * 64,
            "effect_digest": "c" * 64,
            "plan_digest": "d" * 64,
            "claim": {"operation": "openspec.archive", "effect": "c" * 64},
            "source": "archive_commit",
            "authorized_paths": ["openspec/changes/archive/previous/tasks.md"],
        }
    )
    resolution = CurrentResolution(
        verdict="pass",
        authority=CurrentAuthority(
            verdict="pass",
            reason="not_required",
            branch="candidate/dev",
            actor="agent:test:case:agent-test",
            lease={},
            current_head=head,
            current_tree=git(candidate, "rev-parse", "HEAD^{tree}"),
            required=False,
        ),
        commitment=None,
        scope=CurrentScope(paths or (), archive_authority=archive_authority),
    )
    plan = proof_plan(candidate, resolution=resolution)
    assert plan.commitment is None
    assert plan.inputs.commitment is None
    assert plan.facts["values"]["change_id"] == ""
    assert mutable_json(plan.prior_attestations) == (
        {"openspec_archive": archive_authority} if paths else {}
    )
    assert plan.required_gaps == (("proof_archive_scope_stale",) if paths else ())
    if paths is None:
        record = issue_conformant_proof(candidate, head, plan=plan)
        assert record.commitment_digest is None
        assert persist_proof_attestation(candidate, record)["added"] == (record.id,)
        assert_selected_proof(candidate, head, selected=record)
        assert proof_module.proof_for_repository_transition(candidate, head) == (record, [])


@pytest.mark.parametrize(
    ("location", "updates", "gap"),
    [
        *(
            ("body", {field: value}, gap)
            for field, value, gap in literal_case(
                "kernel.test_proof_plan_binding:parametrize:test_proof_predicate_evidence_drift_fails_closed:0"
            )
        ),
        ("envelope", {"predicate": "experiment:novel"}, "proof_not_proven"),
        ("envelope", {"plan_digest": "0" * 64}, "proof_attestation_binding_mismatch:plan_digest"),
        ("envelope", {"policy_digest": "0" * 64}, "proof_policy_digest_stale"),
        ("payload", {"kind": "proof:future-execution"}, "proof_attestation_payload_kind_invalid"),
    ],
)
def test_proof_drift_fails_closed_at_its_exact_layer(tmp_path, location, updates, gap):
    """Body, envelope and payload-kind mutations retain separate rejection claims."""
    repo, head = proof_repository(tmp_path / "repo")
    valid = _issue(repo, head)
    if location == "body":
        updates = {"body": valid.payload.body | updates}
    elif location == "payload":
        updates = {"payload": {"body": valid.payload.body, **updates}}
    store_proof(repo, reissue_attestation(valid, **updates))
    assert_selected_proof(repo, head, gap=gap)


def test_proof_statement_validation_rejects_each_bound_envelope_dimension(tmp_path: Path) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    checks = conformant_proof_checks(plan)
    valid = _issue(repo, head, plan=plan, checks=checks)

    for field, value, expected in (
        ("plan", None, "proof_attestation_plan_missing"),
        (
            "plan",
            plan.model_dump(mode="json") | {"digest": "0" * 64},
            "proof_attestation_plan_digest_mismatch",
        ),
        ("required_gaps", "invalid", "proof_attestation_required_gaps_invalid"),
    ):
        assert proof_statement_gaps(
            reissue_attestation(valid, body=valid.payload.body | {field: value}), checks
        ) == [expected]

    failed_check = checks[0] | {"verdict": "block", "trust_bearing": False}
    result_gaps = proof_statement_gaps(
        reissue_attestation(
            valid,
            verdict="block",
            body={
                **valid.payload.body,
                "claim": {"objective": "prove repository", "verdict": "block"},
            },
        ),
        (failed_check, *checks[1:]),
    )
    assert "proof_attestation_verdict_block" in result_gaps
    assert "proof_attestation_check_not_passed" in result_gaps

    nonconformant = checks[0] | {"action_id": "other", "command": ["other"]}
    gate_gaps = proof_statement_gaps(valid, (nonconformant, *checks[1:]))
    assert "proof_attestation_check_plan_mismatch" in gate_gaps
    assert f"proof_gate_not_policy_conformant:{plan.nodes[0].id}" in gate_gaps

    assert "trust_bearing_proof_missing" in proof_statement_gaps(
        valid,
        tuple(check | {"trust_bearing": False} for check in checks),
    )


@pytest.mark.parametrize("case", ["descriptor", "digest"])
def test_proof_artifact_binding_drift_fails_closed(tmp_path: Path, case: str) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    valid = _issue(repo, head)
    persist_proof_attestation(repo, valid)
    descriptor = valid.payload.body["artifact"]
    assert isinstance(descriptor, Mapping)
    if case == "descriptor":
        forged = reissue_attestation(
            valid,
            body=valid.payload.body
            | {"artifact": descriptor | {"media_type": "text/plain", "extra": "unbound"}},
        )
        assert artifact_checks(proof_artifact_root(repo), forged)[1] == [
            "proof_attestation_artifact_binding_mismatch"
        ]
    else:
        (proof_artifact_root(repo) / str(descriptor["path"])).write_text("tampered")
        assert_selected_proof(repo, head, gap="proof_attestation_artifact_digest_mismatch")


@pytest.mark.parametrize("drift", ["tree", "head"])
def test_proof_issuance_rechecks_live_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    if drift == "head":
        commit_fixture_file(repo, "next.txt", "next\n", "advance after plan")
    else:
        monkeypatch.setattr(proof_module, "current_tree", lambda *_args, **_kwargs: "0" * 40)
    with pytest.raises(ValueError, match="proof_attestation_live_facts_stale"):
        issue_conformant_proof(repo, head, plan=plan, issuer="agent:test:case:proof")


def test_proof_issuance_reuses_the_plan_commitment_without_rereading_exact_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    write_active_commitment(repo, change_id="frozen-proof-binding")
    head = commit_fixture(repo, "freeze proof intent")
    plan = current_proof_plan(repo, expected_head=head)
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    observed = Mock(wraps=proof_module.resolve_gate_policy)
    monkeypatch.setattr(proof_module, "resolve_gate_policy", observed)

    attestation = issue_conformant_proof(repo, head, plan=plan)

    assert attestation.commitment_digest == plan.inputs.commitment
    assert observed.call_count == 1


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ({"plan": None}, "proof_attestation_plan_invalid"),
        ({"checks": []}, "proof_attestation_checks_invalid"),
        ({"issuer": 1}, "proof_attestation_payload_invalid"),
        ({"scope": ""}, "proof_attestation_payload_invalid"),
        ({"verdict": "maybe"}, "proof_attestation_verdict_invalid"),
        ({"issued_at": "now"}, "proof_attestation_issued_at_invalid"),
        ({"required_gaps": []}, "proof_attestation_required_gaps_invalid"),
        ({"required_gaps": (1,)}, "proof_attestation_required_gaps_invalid"),
        ({"boundary": "unrecognized"}, "proof_attestation_boundary_mismatch"),
        ("blocked-plan", "proof_plan_not_admitted"),
        ({"required_gaps": ("unresolved",)}, "proof_attestation_verdict_mismatch"),
        ("missing-check", "proof_attestation_check_plan_mismatch"),
    ],
)
def test_proof_issuance_payload_is_a_closed_contract(tmp_path, updates, error):
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    checks = conformant_proof_checks(plan)
    if updates == "blocked-plan":
        updates = {
            "plan": compile_plan(
                Commitment.model_validate(dict(plan.commitment)),
                Facts.model_validate(plan.facts | {"observed_at": datetime.now(UTC)}),
                plan.nodes,
                policy=dict(plan.policy),
                prior_attestations=dict(plan.prior_attestations),
                required_gaps=("unresolved",),
            )
        }
    elif updates == "missing-check":
        updates = {"checks": checks[:-1]}
    payload = {
        "plan": plan,
        "checks": checks,
        "verdict": "pass",
        "issuer": "agent:test:case:proof",
        "scope": "repository",
        "boundary": "repository",
    }
    with pytest.raises((TypeError, ValueError), match=error):
        issue_proof_attestation(repo, payload | updates)


@pytest.fixture
def work_proof(tmp_path, monkeypatch):
    holder = "agent:test:case:proof-holder"
    root = prepared_work_lane(tmp_path, holder_ref=holder).worktree
    head = git(root, "rev-parse", "HEAD")
    lease = dict(proof_module.leases_by_branch(root)["work/feature"])
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    resolution = CurrentResolution(
        verdict="pass",
        authority=CurrentAuthority(
            verdict="pass",
            reason="matched",
            branch="work/feature",
            actor=holder,
            lease=lease,
            current_head=head,
            current_tree=git(root, "rev-parse", "HEAD^{tree}"),
        ),
        commitment=commitment_fixture(id="change:fixture-change"),
        scope=CurrentScope(("FEATURE.md",)),
    )
    return root, head, resolution


def test_work_lane_proof_plan_compiles_only_from_the_frozen_resolution(work_proof, monkeypatch):
    root, head, resolution = work_proof

    def reread(*_args, **_kwargs):
        pytest.fail("proof planning must use the frozen authority and Git facts")

    for name in ("leases_by_branch", "resolve_current_authority", "current_branch", "current_tree"):
        monkeypatch.setattr(proof_module, name, reread)
    plan = proof_plan(root, resolution=resolution)
    assert mutable_json(plan.commitment) == resolution.commitment.model_dump(mode="json")
    assert plan.facts["head"] == head
    assert plan.facts["tree"] == resolution.authority.current_tree
    assert plan.facts["values"]["changed_paths"] == ("FEATURE.md",)
    assert plan.facts["values"]["lease_generation"] == {
        key: resolution.lease[key] for key in ("lane_ref", "generation", "holder_ref", "expires_at")
    }


@pytest.mark.parametrize(
    ("drift", "gap"),
    [
        ("generation", "proof_lease_generation_stale"),
        ("actor", "lease_holder_mismatch"),
        ("branch", "proof_attestation_live_facts_stale"),
    ],
)
def test_work_lane_proof_issuance_rechecks_live_authority(work_proof, monkeypatch, drift, gap):
    root, head, resolution = work_proof
    plan = proof_plan(root, resolution=resolution)
    if drift == "generation":
        monkeypatch.setattr(
            proof_module,
            "leases_by_branch",
            lambda _root: {
                "work/feature": resolution.lease
                | {"generation": int(resolution.lease["generation"]) + 1}
            },
        )
    elif drift == "branch":
        git(root, "switch", "--detach", head)
    else:
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    with pytest.raises(ValueError, match=gap):
        issue_conformant_proof(root, head, plan=plan)


@pytest.mark.parametrize(
    ("verdict", "gaps", "coordinate", "error"),
    [
        ("block", ("intent_missing",), "", "intent_missing"),
        ("unknown", (), "", "unknown"),
        ("pass", (), "authority", "current_authority_unavailable"),
        ("pass", (), "current_head", "current_authority_unavailable"),
        ("pass", (), "current_tree", "current_authority_unavailable"),
    ],
)
def test_proof_plan_rejects_unresolved_authority(tmp_path, verdict, gaps, coordinate, error):
    authority = CurrentAuthority(
        verdict="pass",
        reason="matched",
        branch="work/fixture",
        actor="agent:test:case:owner",
        lease={},
        current_head="a" * 40,
        current_tree="b" * 40,
    )
    if coordinate == "authority":
        authority = None
    elif coordinate:
        authority = replace(authority, **{coordinate: ""})
    resolution = CurrentResolution(
        verdict=verdict,
        authority=authority,
        commitment=None,
        scope=CurrentScope(()),
        required_gaps=gaps,
    )
    with pytest.raises(ValueError, match=error):
        proof_plan(tmp_path, resolution=resolution)
