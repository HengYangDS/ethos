from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.proof as proof_module
import ethos.adapters.openspec.profile as openspec_profile
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import artifact_checks
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from ethos.contracts.value import mutable_json
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import conformant_proof_check
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import issue_conformant_proof
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.governed_repository import write_active_commitment
from tests.support.governed_repository import write_script_gate_policy
from tests.support.literal_cases import literal_case

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
    payload = record.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
    return Attestation.issue(payload | updates)


def _store(root: Path, record: Attestation) -> None:
    store = attestation_store_dir(root)
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{record.id}.json").write_text(record.canonical_json(), encoding="utf-8")


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
    carrier.write_text(carrier.read_text() + 'acceptance=["current"]\n')
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    plan = proof_plan(root, head=git(root, "rev-parse", "HEAD"))
    dated = Commitment.model_validate(plan.commitment | {"id": "change:20260809-proof-binding"})
    monkeypatch.setattr(openspec_profile, "load_lease_bound_commitment", lambda *_a, **_k: dated)
    proof_plan(root, head=git(root, "rev-parse", "HEAD"))


def test_proof_attestation_is_content_addressed_and_exactly_bound(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    plan = proof_plan(repo, head=head)
    record = _issue(repo, head)
    path = persist_proof_attestation(repo, record)
    assert path.read_text() == record.canonical_json()
    assert record.predicate == "proof:execution"
    assert record.subject == f"git:commit:{head}"
    assert record.verdict == "pass"
    assert record.commitment_digest == plan.inputs.commitment
    assert record.facts_digest == plan.inputs.facts
    assert record.plan_digest == plan.digest
    assert record.policy_digest == plan.inputs.policy
    artifact = record.statement["artifact"]
    assert isinstance(artifact, Mapping)
    digest = str(artifact["sha256"]).removeprefix("sha256:")
    assert record.effect_digest == plan.inputs.effect != digest
    assert record.evidence_refs == (f"sha256:{digest}",)
    assert mutable_json(record.statement["plan"]) == plan.model_dump(mode="json")
    assert set(record.statement) == {
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
    _store(repo, _reissue(valid, statement=valid.statement | {field: value}))
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


@pytest.mark.parametrize("case", ["descriptor", "digest"])
def test_proof_artifact_binding_drift_fails_closed(tmp_path: Path, case: str) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    valid = _issue(repo, head)
    persist_proof_attestation(repo, valid)
    descriptor = valid.statement["artifact"]
    assert isinstance(descriptor, Mapping)
    if case == "descriptor":
        forged = _reissue(
            valid,
            statement=valid.statement
            | {"artifact": descriptor | {"media_type": "text/plain", "extra": "unbound"}},
        )
        assert artifact_checks(attestation_store_dir(repo), forged)[1] == [
            "proof_attestation_artifact_binding_mismatch"
        ]
    else:
        (attestation_store_dir(repo) / str(descriptor["path"])).write_text("tampered")
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
            statement=valid.statement | {"plan": forged.model_dump(mode="json")},
        ),
    )
    _assert_proof(repo, head, gap=gap)


def test_persistence_identity_and_self_contained_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    record = _issue(repo, head)
    path = persist_proof_attestation(repo, record)
    assert persist_proof_attestation(repo, record) == path
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
    path.write_text("{}")
    with pytest.raises(ValueError, match="attestation_identity_collision"):
        persist_proof_attestation(repo, record)


def test_repository_admission_prefers_full_proof(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo, full=True)
    (repo / ".ethos/commitment.toml").write_text(
        'schema_version=1\nid="repository:repo"\nintent="govern"\n'
        'subjects=["repository:repo"]\nscope=["**"]\n'
    )
    commitment = repo / "openspec/changes/proof-binding"
    commitment.mkdir(parents=True)
    (commitment / "commitment.toml").write_text(
        'schema_version=1\nid="change:proof-binding"\nintent="proof"\nsubjects=["repository:self"]\nscope=["**"]\n'
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
        statement=first.statement | {"claim": {"objective": "conflict", "verdict": "pass"}},
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
            **({"statement": current.statement | {"novel_semantics": True}} if novel else {}),
        ),
    )
    _assert_proof(repo, head, selected=current)
    _store(repo, _reissue(current, statement=current.statement | {"scope": ("workspace",)}))
    _assert_proof(repo, head, selected=current)
