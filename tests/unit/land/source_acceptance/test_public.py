"""Public source-purpose journeys use audit/quality doubles and real Git effects."""

from __future__ import annotations

import json
import tomllib
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.mutation.landing as landing
import ethos.adapters.repo.dependency_acceptance as acceptance
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.mutation.proof_admission import proof_attestation
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import product_audit_projection
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import WorkLaneFixture
from tests.support.governed_repository import git
from tests.unit.land.source_acceptance.support import EXPIRED
from tests.unit.land.source_acceptance.support import prepare_source
from tests.unit.land.source_acceptance.support import prove_source

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def _expired_recovery(work: Path, args: tuple[str, ...], proof: Attestation, monkeypatch) -> None:
    policy = tomllib.loads((work / AUDIT_POLICY_PATH).read_text())
    expired = policy["dispositions"][0]["expires_at"] + timedelta(seconds=1)

    class ExpiredClock(datetime):
        @classmethod
        def now(cls, _tz=None):
            return expired

    with monkeypatch.context() as expired_context:
        expired_context.setattr(acceptance, "datetime", ExpiredClock)
        selected, gaps = proof_attestation(
            work,
            proof.subject.removeprefix("git:commit:"),
            store=proof_artifact_root(work),
            attestation_id=proof.id,
            acceptance_purpose="local-source",
        )
        assert selected is None
        assert EXPIRED in gaps
        denied = run_ethos_blocked(*args, cwd=work)
        assert EXPIRED in denied["required_gaps"]


def _product_drift_refusal(work: Path, args: tuple[str, ...], monkeypatch) -> None:
    """A saved proof cannot authorize effects after selected product-policy drift."""
    with monkeypatch.context() as drifted:
        path = acceptance.canonical_resource(AUDIT_POLICY_PATH)
        changed = tomllib.loads(path.read_text())
        changed["summary"] = "Changed selected product policy after proof"
        product = work.parent / "selected-product" / AUDIT_POLICY_PATH
        product.parent.mkdir(parents=True, exist_ok=True)
        product.write_bytes(product_audit_projection(tomli_w.dumps(changed).encode()))
        drifted.setattr(acceptance, "canonical_resource", lambda _name: product)
        ref = f"refs/heads/{load_branch_role_policy(work).candidate_branch}"
        before = git(work, "rev-parse", ref)

        def forbidden(*_args, **_options):
            pytest.fail("changed product cannot authorize CAS or worktree sync")

        drifted.setattr(git_effects, "_apply_git_ref_transaction", forbidden)
        drifted.setattr(landing, "sync_worktree", forbidden)
        denied = run_ethos_blocked(*args, cwd=work)
        assert (
            "proof_dependency_acceptance:dependency_audit_product_policy_changed"
            in denied["required_gaps"]
        )
        assert git(work, "rev-parse", ref) == before


def _land_source(
    work: Path, args: tuple[str, ...], proof: Attestation, monkeypatch, *, recover: bool
) -> dict:
    if not recover:
        return run_ethos(*args, cwd=work)

    def fail_sync(*_args, **_options):
        message = "fixture: sync interrupted after real CAS"
        raise ValueError(message)

    with monkeypatch.context() as interrupted:
        interrupted.setattr(landing, "sync_worktree", fail_sync)
        blocked = run_ethos_blocked(*args, cwd=work)
    assert blocked["required_gaps"] == ["candidate_worktree_sync_failed"]
    state = blocked["data"]["candidate_update"]
    effect_id = state["attestation"]["id"]
    plan_digest = state["attestation"]["plan_digest"]
    ref = f"refs/heads/{load_branch_role_policy(work).candidate_branch}"
    assert git(work, "rev-parse", ref) == proof.subject.removeprefix("git:commit:")
    _expired_recovery(work, args, proof, monkeypatch)
    _product_drift_refusal(work, args, monkeypatch)
    landed = run_ethos(*args, cwd=work)
    completed = landed["data"]["candidate_update"]
    assert completed["cas_attempts"] == 0
    assert completed["attestation"]["plan_digest"] == plan_digest
    assert completed["attestation"]["id"] == effect_id
    return landed


def _delivery_boundaries(
    fixture: WorkLaneFixture, head: str, before: str, proof: Attestation
) -> None:
    repo, work = fixture.repository, fixture.worktree
    roles = load_branch_role_policy(repo)
    strict = run_ethos_blocked("land", "--apply", "--authorize", "--json", cwd=work)
    assert "proof_acceptance_purpose_mismatch" in strict["required_gaps"]
    for target, options in (
        (repo, ("--closeout",)),
        (repo.parent / "repo-release", ("--release",)),
    ):
        denied = run_ethos_blocked(
            "land",
            *options,
            "--apply",
            "--authorize",
            "--acceptance-purpose",
            "local-source",
            "--json",
            cwd=target,
        )
        assert denied["required_gaps"] == ["local_source_acceptance_effect_forbidden"]
    assert git(repo, "rev-parse", roles.accepted_branch) == before
    assert git(repo, "rev-parse", roles.release_branch) == before
    proofs = [
        item.id
        for item in read_attestation_set(work)[1]
        if item.predicate == "proof:execution" and item.subject == f"git:commit:{head}"
    ]
    assert proofs == [proof.id]


@pytest.mark.parametrize("recover", [False, True], ids=["normal", "recover"])
def test_public_source_acceptance(
    tmp_path: Path, monkeypatch, audit_attempts: list[str], *, recover: bool
) -> None:
    """Prove, CAS and recover publicly without seeding a stricter proof."""
    actor = "agent:test:case:agent-test"
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    monkeypatch.delenv("CI", raising=False)
    fixture, before, head = prepare_source(tmp_path, actor)
    work = fixture.worktree
    assert not (fixture.candidate / ".venv").exists()
    stdout_attempts = audit_attempts
    proof = prove_source(work, head, stdout_attempts)
    roles = load_branch_role_policy(work)
    effect = roles.candidate_effect(
        branch=roles.work_branch("source"),
        current_head=head,
        candidate_head=before,
    )
    transactions = []
    original_git = git_effects.run_git

    def transact(root, *arguments, **options):
        if arguments[:2] == ("update-ref", "--stdin"):
            assert options["stdin"] == effect.program()
            transactions.append(options["stdin"])
        return original_git(root, *arguments, **options)

    monkeypatch.setattr(git_effects, "run_git", transact)
    args = (
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--acceptance-purpose",
        "local-source",
        "--json",
    )
    _product_drift_refusal(work, args, monkeypatch)
    landed = _land_source(work, args, proof, monkeypatch, recover=recover)
    assert landed["verdict"] == "pass"
    assert landed["data"]["candidate_update"]["state"] == "candidate_validated"
    assert landed["data"]["candidate_update"]["path"] == fixture.candidate.resolve().as_posix()
    assert git(fixture.candidate, "write-tree") == git(work, "rev-parse", f"{head}^{{tree}}")
    _delivery_boundaries(fixture, head, before, proof)
    assert len(stdout_attempts) == len(transactions) == 1


@pytest.mark.parametrize("scan_passes", [False, True], ids=["native-refusal", "native-acceptance"])
def test_public_native_source_acceptance(
    tmp_path: Path, monkeypatch, audit_attempts: list[str], *, scan_passes: bool
) -> None:
    """The declared native check owns applicability and still controls proof and CAS."""
    actor = "agent:test:case:agent-test"
    monkeypatch.setenv("ETHOS_ACTOR", actor)
    fixture, before, head = prepare_source(tmp_path, actor, native_scan=scan_passes)
    work = fixture.worktree
    assert not any((work / name).exists() for name in ("pyproject.toml", "uv.lock"))
    arguments = (
        "prove",
        "--full",
        "--execute",
        "--expect-head",
        head,
        "--acceptance-purpose",
        "local-source",
        "--json",
    )
    completed = run_ethos_raw(*arguments, cwd=work)
    result = json.loads(completed.stdout)
    assert completed.returncode == (0 if scan_passes else 1), result
    roles = load_branch_role_policy(work)
    if not scan_passes:
        assert result["verdict"] == "block"
        assert git(fixture.candidate, "rev-parse", "HEAD") == before
        assert not any(
            item.predicate == "proof:execution" and item.subject == f"git:commit:{head}"
            for item in read_attestation_set(work)[1]
        )
        return
    proof = result["data"]["attestation"]
    selected, gaps = proof_attestation(
        work,
        head,
        store=proof_artifact_root(work),
        attestation_id=proof["id"],
        acceptance_purpose="local-source",
    )
    assert selected is not None
    assert not gaps
    assert {gate["id"] for gate in proof["payload"]["body"]["plan"]["policy"]["gates"]} == {
        "behavior",
        "static",
        "native-dependencies",
        "config-quality",
        "docs-registry",
        "markdown-lint",
        "markdown-links",
        "openspec",
        "prose",
        "schemas",
        "source-format",
    }
    landed = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--acceptance-purpose",
        "local-source",
        "--json",
        cwd=work,
    )
    assert landed["verdict"] == "pass"
    assert git(fixture.candidate, "rev-parse", "HEAD") == head
    assert git(fixture.repository, "rev-parse", roles.accepted_branch) == before
    assert not audit_attempts
