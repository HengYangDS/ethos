from __future__ import annotations

import tomllib
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.mutation.proof as proof_module
import ethos.adapters.openspec.profile as openspec_profile
from ethos.adapters.mutation import proof_admission
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.mutation.proof_validation import proof_statement_gaps
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.value import mutable_json
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import conformant_proof_check
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import issue_conformant_proof
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.governed_repository import write_active_commitment
from tests.support.governed_repository import write_script_gate_policy
from tests.support.literal_cases import literal_case
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from pathlib import Path


def _adopted_repo(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path)
    adopt_and_commit(repo)
    write_active_commitment(repo, change_id="proof-binding")
    return repo, commit_fixture(repo, "bind proof")


def _issue(
    root: Path,
    head: str,
    *,
    plan: TransitionPlan | None = None,
    checks: tuple[dict[str, object], ...] | None = None,
    issuer: str = "agent:test:case:proof",
    issued_at: datetime = datetime(2026, 7, 26, tzinfo=UTC),
    boundary: str = "repository",
) -> Attestation:
    return issue_conformant_proof(
        root,
        head,
        plan=plan,
        checks=checks,
        issuer=issuer,
        issued_at=issued_at,
        boundary=boundary,
    )


def _reissue(record: Attestation, **updates: object) -> Attestation:
    body = updates.pop("body", None)
    payload = record.model_dump(mode="python", exclude={"id"})
    if body is not None:
        payload["payload"] = {"kind": record.payload.kind, "body": body}
    return Attestation.issue(payload | updates)


def _store(root: Path, record: Attestation, *, selected: bool = True) -> None:
    store = proof_artifact_root(root)
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{record.id}.json").write_text(record.canonical_json(), encoding="utf-8")
    if selected:
        record_attestations(root, (record,))


def _assert_proof(
    root: Path, head: str, *, selected: Attestation | None = None, gap: str | None = None
) -> None:
    assert proof_attestation(root, head) == selected
    assert proof_gaps(root, head) == ([] if gap is None else [gap])


def test_work_lane_proof_plan_uses_the_current_active_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:current-commitment"
    root = start_adopted_work_lane(tmp_path, holder_ref=holder).worktree
    lease = proof_module.leases_by_branch(root)["work/feature"]
    carrier = root / str(lease["base_commitment_path"])
    current = Commitment.model_validate(tomllib.loads(carrier.read_text()))
    carrier.write_text(
        tomli_w.dumps(
            current.model_copy(update={"acceptance": ("current",)}).model_dump(mode="python")
        )
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    plan = proof_plan(root, head=git(root, "rev-parse", "HEAD"))
    dated = Commitment.model_validate(plan.commitment | {"id": "change:20260809-proof-binding"})
    monkeypatch.setattr(openspec_profile, "load_lease_bound_commitment", lambda *_a, **_k: dated)
    proof_plan(root, head=git(root, "rev-parse", "HEAD"))


def test_proof_attestation_is_content_addressed_and_exactly_bound(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    record = _issue(repo, head)
    selected = persist_proof_attestation(repo, record)
    assert selected["root"]
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
    _assert_proof(repo, head, selected=record)


@pytest.mark.parametrize(
    ("field", "value", "gap"),
    literal_case(
        "kernel.test_proof_plan_binding:parametrize:test_proof_predicate_evidence_drift_fails_closed:0"
    ),
)
def test_proof_predicate_evidence_drift_fails_closed(
    tmp_path: Path, field: str, value: object, gap: str
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    _store(repo, _reissue(valid, body=valid.payload.body | {field: value}))
    _assert_proof(repo, head, gap=gap)


@pytest.mark.parametrize(
    ("updates", "gap"),
    [
        ({"predicate": "experiment:novel"}, "proof_not_proven"),
        ({"plan_digest": "0" * 64}, "proof_attestation_binding_mismatch:plan_digest"),
        ({"policy_digest": "0" * 64}, "proof_policy_digest_stale"),
    ],
)
def test_proof_envelope_binding_drift_fails_closed(
    tmp_path: Path, updates: dict[str, object], gap: str
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    _store(repo, _reissue(_issue(repo, head), **updates))
    _assert_proof(repo, head, gap=gap)


def test_unknown_proof_payload_kind_cannot_authorize(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    payload = valid.model_dump(mode="python", exclude={"id"})
    payload["payload"] = {
        "kind": "proof:future-execution",
        "body": valid.payload.body,
    }
    _store(repo, Attestation.issue(payload))

    _assert_proof(repo, head, gap="proof_attestation_payload_kind_invalid")


@pytest.mark.parametrize("case", ["descriptor", "digest"])
def test_proof_artifact_binding_drift_fails_closed(tmp_path: Path, case: str) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    persist_proof_attestation(repo, valid)
    descriptor = valid.payload.body["artifact"]
    assert isinstance(descriptor, Mapping)
    if case == "descriptor":
        forged = _reissue(
            valid,
            body=valid.payload.body
            | {"artifact": descriptor | {"media_type": "text/plain", "extra": "unbound"}},
        )
        assert artifact_checks(proof_artifact_root(repo), forged)[1] == [
            "proof_attestation_artifact_binding_mismatch"
        ]
    else:
        (proof_artifact_root(repo) / str(descriptor["path"])).write_text("tampered")
        _assert_proof(repo, head, gap="proof_attestation_artifact_digest_mismatch")


def test_proof_issuance_rechecks_live_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    monkeypatch.setattr(proof_module, "current_tree", lambda *_args, **_kwargs: "0" * 40)
    with pytest.raises(ValueError, match="proof_attestation_live_facts_stale"):
        issue_conformant_proof(repo, head, plan=plan, issuer="agent:test:case:proof")


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("plan", "proof_attestation_plan_invalid"),
        ("checks", "proof_attestation_checks_invalid"),
        ("payload", "proof_attestation_payload_invalid"),
        ("empty", "proof_attestation_payload_invalid"),
        ("verdict", "proof_attestation_verdict_invalid"),
        ("issued-at", "proof_attestation_issued_at_invalid"),
        ("required-gaps-shape", "proof_attestation_required_gaps_invalid"),
        ("required-gaps-item", "proof_attestation_required_gaps_invalid"),
    ],
)
def test_proof_issuance_payload_is_a_closed_contract(
    tmp_path: Path,
    case: str,
    error: str,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    checks = tuple(conformant_proof_check(node.id, repo, tree_ref=head) for node in plan.nodes)
    payload: dict[str, object] = {
        "plan": plan,
        "checks": checks,
        "verdict": "pass",
        "issuer": "agent:test:case:proof",
        "scope": "repository",
        "boundary": "repository",
    }
    updates: dict[str, object] = {
        "plan": None,
        "checks": list(checks),
        "payload": {"issuer": 1},
        "empty": {"scope": ""},
        "verdict": {"verdict": "maybe"},
        "issued-at": {"issued_at": "now"},
        "required-gaps-shape": {"required_gaps": []},
        "required-gaps-item": {"required_gaps": (1,)},
    }
    update = updates[case]
    if isinstance(update, dict):
        payload.update(update)
    else:
        payload[case] = update

    with pytest.raises((TypeError, ValueError), match=error):
        issue_proof_attestation(repo, payload)


def test_proof_issuance_rejects_nonadmitted_plan_and_result_drift(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    admitted = proof_plan(repo, head=head)
    checks = tuple(conformant_proof_check(node.id, repo, tree_ref=head) for node in admitted.nodes)
    blocked = compile_plan(
        Commitment.model_validate(dict(admitted.commitment)),
        Facts.model_validate(admitted.facts | {"observed_at": datetime.now(UTC)}),
        admitted.nodes,
        policy=dict(admitted.policy),
        prior_attestations=dict(admitted.prior_attestations),
        required_gaps=("unresolved",),
    )
    payload = {
        "plan": blocked,
        "checks": checks,
        "verdict": "pass",
        "issuer": "agent:test:case:proof",
        "scope": "repository",
        "boundary": "repository",
    }
    with pytest.raises(ValueError, match="proof_plan_not_admitted"):
        issue_proof_attestation(repo, payload)

    payload["plan"] = admitted
    payload["required_gaps"] = ("unresolved",)
    with pytest.raises(ValueError, match="proof_attestation_verdict_mismatch"):
        issue_proof_attestation(repo, payload)

    payload["required_gaps"] = ()
    payload["checks"] = checks[:-1]
    with pytest.raises(ValueError, match="proof_attestation_check_plan_mismatch"):
        issue_proof_attestation(repo, payload)


@pytest.mark.parametrize(
    ("state", "gap"),
    [
        ("expired", "work_lane_lease_expired"),
        ("head", "lease_head_stale"),
        ("actor", "lease_actor_mismatch"),
    ],
)
def test_work_lane_proof_plan_requires_current_lease_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    gap: str,
) -> None:
    holder = "agent:test:case:proof-holder"
    root = start_adopted_work_lane(tmp_path, holder_ref=holder).worktree
    head = git(root, "rev-parse", "HEAD")
    lease = dict(proof_module.leases_by_branch(root)["work/feature"])
    monkeypatch.setenv("ETHOS_ACTOR", "other" if state == "actor" else holder)
    if state == "expired":
        lease["lease_state"] = "expired"
    elif state == "head":
        lease["expected_head"] = "0" * 40
    monkeypatch.setattr(
        proof_module,
        "leases_by_branch",
        lambda _root: {"work/feature": lease},
    )

    with pytest.raises(ValueError, match=gap):
        proof_plan(root, head=head)


@pytest.mark.parametrize(
    ("case", "gap"),
    literal_case(
        "kernel.test_proof_plan_binding:parametrize:test_proof_admission_rechecks_live_plan_closure:1"
    ),
)
def test_proof_admission_rechecks_live_plan_closure(tmp_path: Path, case: str, gap: str) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    plan = proof_plan(repo, head=head)
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
    _store(
        repo,
        _reissue(
            valid,
            commitment_digest=forged.inputs.commitment,
            facts_digest=forged.inputs.facts,
            plan_digest=forged.digest,
            policy_digest=forged.inputs.policy,
            effect_digest=forged.inputs.effect,
            body=valid.payload.body | {"plan": forged.model_dump(mode="json")},
        ),
    )
    _assert_proof(repo, head, gap=gap)


def test_persistence_identity_and_self_contained_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    record = _issue(repo, head)
    selected = persist_proof_attestation(repo, record)
    repeated = persist_proof_attestation(repo, record)
    assert repeated["root"] == selected["root"]
    assert repeated["added"] == ()
    monkeypatch.setattr(
        proof_module,
        "load_profile_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError()),
    )
    monkeypatch.setattr(
        proof_module,
        "load_repository_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError()),
    )
    _assert_proof(repo, head, selected=record)


def test_local_only_proof_outside_selected_attestation_set_is_ignored(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    record = _issue(repo, head)
    _store(repo, record, selected=False)

    _assert_proof(repo, head, gap="proof_not_proven")


def test_selected_attestation_member_with_exact_local_artifact_can_authorize(
    tmp_path: Path,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    record = _issue(repo, head)
    selected = persist_proof_attestation(repo, record)

    root, members = read_attestation_set(repo)

    assert root == selected["root"]
    assert members == (record,)
    _assert_proof(repo, head, selected=record)


def test_selected_attestation_membership_without_exact_local_artifact_cannot_authorize(
    tmp_path: Path,
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    record = _issue(repo, head)
    record_attestations(repo, (record,))
    artifact = record.payload.body["artifact"]
    assert isinstance(artifact, Mapping)
    (proof_artifact_root(repo) / str(artifact["path"])).unlink()

    _assert_proof(repo, head, gap="proof_attestation_artifact_missing")


def test_repository_admission_prefers_full_proof(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo, full=True)
    (repo / ".ethos/commitment.toml").write_text(
        tomli_w.dumps(
            commitment_v2(
                id="repository:repo",
                intent="govern",
                subjects=("repository:repo",),
                scope=("**",),
            ).model_dump(mode="python")
        )
    )
    commitment = repo / "openspec/changes/proof-binding"
    commitment.mkdir(parents=True)
    (commitment / "commitment.toml").write_text(
        tomli_w.dumps(
            commitment_v2(
                id="change:proof-binding",
                intent="proof",
                subjects=("repository:repo",),
                scope=("**",),
            ).model_dump(mode="python")
        )
    )
    head = commit_fixture(repo, "full floor")
    default = _issue(repo, head)
    persist_proof_attestation(repo, default)
    _assert_proof(repo, head, gap="full_proof_required")
    full_plan = proof_plan(repo, head=head, full=True)
    full = _issue(
        repo,
        head,
        plan=full_plan,
    )
    persist_proof_attestation(repo, full)
    assert default.plan_digest != full.plan_digest
    _assert_proof(repo, head, selected=full)


def test_repository_authority_ignores_a_retired_work_lane_proof(
    tmp_path: Path,
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    head = commit_fixture_file(fixture.worktree, "FEATURE.md", "feature\n", "feature")
    historical = _issue(fixture.worktree, head)
    persist_proof_attestation(fixture.worktree, historical)
    git(fixture.candidate, "reset", "--hard", head)
    historical_plan = proof_plan(fixture.candidate, head=head)
    values = dict(historical_plan.facts["values"])
    values["change_id"] = ""
    values.pop("lease_generation", None)
    repository_plan = compile_plan(
        load_repository_commitment(fixture.candidate, tree_ref=head),
        Facts.model_validate(
            historical_plan.facts | {"observed_at": datetime.now(UTC), "values": values}
        ),
        historical_plan.nodes,
        policy=dict(historical_plan.policy),
    )
    repository = _reissue(
        historical,
        commitment_digest=repository_plan.inputs.commitment,
        facts_digest=repository_plan.inputs.facts,
        plan_digest=repository_plan.digest,
        policy_digest=repository_plan.inputs.policy,
        effect_digest=repository_plan.inputs.effect,
        body=historical.payload.body | {"plan": repository_plan.model_dump(mode="json")},
    )
    persist_proof_attestation(fixture.candidate, repository)
    assert historical.commitment_digest != repository.commitment_digest
    assert proof_gaps(fixture.candidate, head) == ["stale_binding"]

    selected, gaps = proof_admission.proof_attestation(
        fixture.candidate,
        head,
        authority=load_repository_commitment(fixture.candidate, tree_ref=head),
        store=proof_artifact_root(fixture.candidate),
    )

    assert gaps == []
    assert selected == repository
    wrong = load_repository_commitment(fixture.candidate, tree_ref=head).model_copy(
        update={"acceptance": ("wrong",)}
    )
    assert proof_admission.proof_attestation(
        fixture.candidate,
        head,
        authority=wrong,
        store=proof_artifact_root(fixture.candidate),
    )[1] == ["proof_attestation_commitment_mismatch"]
    checks, gaps = artifact_checks(proof_artifact_root(fixture.candidate), repository)
    assert checks is not None
    assert gaps == []
    former = _reissue(
        repository,
        body=dict(repository.payload.body) | {"head": head},
    )
    assert proof_statement_gaps(former, checks) == ["model_gap"]


def test_equivalent_proofs_supersede_deterministically_but_conflicts_block(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = _issue(repo, head)
    persist_proof_attestation(repo, first)
    later = _reissue(first, issued_at=first.issued_at + timedelta(seconds=1))
    persist_proof_attestation(repo, later)
    assert proof_attestation(repo, head).id == min(first.id, later.id)
    conflict = _reissue(
        first,
        verifier="agent:test:case:conflict",
        body=first.payload.body | {"claim": {"objective": "conflict", "verdict": "pass"}},
    )
    persist_proof_attestation(repo, conflict)
    _assert_proof(repo, head, gap="contradiction")


def test_equivalent_proofs_with_different_artifacts_share_closure(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = _issue(repo, head)
    persist_proof_attestation(repo, first)
    checks = tuple(
        conformant_proof_check(node.id, repo, tree_ref=head) | {"stdout": "again"}
        for node in proof_plan(repo, head=head).nodes
    )
    second = _issue(repo, head, checks=checks, issued_at=first.issued_at + timedelta(seconds=1))
    persist_proof_attestation(repo, second)
    assert first.effect_digest == second.effect_digest
    assert first.evidence_refs != second.evidence_refs
    _assert_proof(repo, head, selected=proof_attestation(repo, head))


def _archive_plan(
    repo: Path, head: str, changed: tuple[str, ...], authorized: tuple[str, ...]
) -> TransitionPlan:
    base = proof_plan(repo, head=head, changed_paths=changed)
    facts = Facts.model_validate(
        base.facts
        | {
            "observed_at": datetime.now(UTC),
            "values": base.facts["values"] | {"changed_paths": changed},
        }
    )
    return compile_plan(
        Commitment.model_validate(dict(base.commitment)),
        facts,
        base.nodes,
        policy=dict(base.policy),
        prior_attestations={"openspec_archive": {"authorized_paths": list(authorized)}},
    )


def test_archive_authority_admits_its_exact_changed_path_subset(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(
        repo, head, plan=_archive_plan(repo, head, ("historical.py", "current.py"), ("current.py",))
    )
    persist_proof_attestation(repo, valid)
    _assert_proof(repo, head, selected=valid)


@pytest.mark.parametrize("novel", [False, True])
def test_expired_or_other_query_proofs_do_not_pollute_current_authority(
    tmp_path: Path, *, novel: bool
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    current = _issue(repo, head)
    persist_proof_attestation(repo, current)
    issued = datetime.now(UTC) - timedelta(minutes=2)
    _store(
        repo,
        _reissue(
            current,
            issued_at=issued,
            valid_from=issued,
            valid_until=issued + timedelta(minutes=1),
            **({"body": current.payload.body | {"novel_semantics": True}} if novel else {}),
        ),
    )
    _assert_proof(repo, head, selected=current)
    _store(repo, _reissue(current, body=current.payload.body | {"scope": ("workspace",)}))
    _assert_proof(repo, head, selected=current)
