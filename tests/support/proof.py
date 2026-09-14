"""Construct policy-bound proof plans and synthetic evidence for isolated tests."""

from __future__ import annotations

import os
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status_observation
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def issue_conformant_proof(
    repo,
    head,
    *,
    plan=None,
    checks=None,
    full=False,
    issuer="agent:test:fixture:proof",
    issued_at=datetime(2026, 7, 26, tzinfo=UTC),
    boundary="repository",
):
    """Issue one proof Attestation from the repository's exact declared policy."""
    plan = plan or current_proof_plan(repo, expected_head=head, full=full)
    if checks is None:
        checks = tuple(conformant_proof_check(node.id, repo, tree_ref=head) for node in plan.nodes)
    return issue_proof_attestation(
        repo,
        {
            "plan": plan,
            "checks": checks,
            "verdict": "pass",
            "issuer": issuer,
            "issued_at": issued_at,
            "scope": "repository",
            "boundary": boundary,
        },
    )


def current_proof_plan(
    repo: Path,
    *,
    expected_head: str,
    gate_ids: tuple[str, ...] = (),
    full: bool = False,
):
    """Compile proof from the production resolution of one exact current HEAD."""
    observed_head = git(repo, "rev-parse", "HEAD")
    if observed_head != expected_head:
        msg = f"fixture_proof_head_not_current:{expected_head}:{observed_head}"
        raise AssertionError(msg)
    status, authority = workspace_status_observation(
        repo,
        include_foreign_path_scope=False,
    )
    resolution = resolve_current_resolution(
        repo,
        status=status,
        authority=authority,
        changed=True,
    )
    if resolution.verdict != "pass":
        msg = "fixture_current_resolution_not_passed:" + ",".join(resolution.required_gaps)
        raise AssertionError(msg)
    return proof_plan(
        repo,
        resolution=resolution,
        gate_ids=gate_ids,
        full=full,
    )


def seed_executed_proof(repo: Path, head: str, *, full: bool = False) -> None:
    """Persist one complete policy-conformant generic proof Attestation."""
    branch = git(repo, "branch", "--show-current")
    holder = str(leases_by_branch(repo).get(branch, {}).get("holder_ref") or "")
    original = os.environ.get("ETHOS_ACTOR")
    hooks_path = git(repo, "config", "--get", "core.hooksPath")
    installed_hooks = not hook_runtime_binding(repo)["required_gaps"]
    if holder:
        os.environ["ETHOS_ACTOR"] = holder
    if installed_hooks:
        git(repo, "config", "--worktree", "core.hooksPath", ".git/test-hooks")
    try:
        persist_proof_attestation(
            repo,
            issue_conformant_proof(
                repo,
                head,
                full=full,
                issued_at=datetime.now(UTC),
            ),
        )
    finally:
        if installed_hooks:
            git(repo, "config", "--worktree", "core.hooksPath", hooks_path)
        if original is None:
            os.environ.pop("ETHOS_ACTOR", None)
        else:
            os.environ["ETHOS_ACTOR"] = original


def conformant_proof_check(gate_id: str, root: Path, *, tree_ref: str) -> dict[str, object]:
    """Build one terminal check result matching one committed gate policy identity."""
    gate = resolve_gate_policy(root, tree_ref=tree_ref, gate_ids=(gate_id,)).registry.get(gate_id)
    if gate is None:
        command: tuple[str, ...] = ("pytest",)
        trust_bearing = True
        evidence_class = "test"
    else:
        command = gate_execution_identity(gate)
        trust_bearing = gate.trust_bearing
        evidence_class = gate.evidence_class
    return {
        "action_id": gate_id,
        "command": list(command),
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "verdict": "pass",
        "evidence_class": evidence_class,
        "trust_bearing": trust_bearing,
        "diagnostics": [],
    }


def proof_repository(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path)
    adopt_and_commit(repo)
    write_active_commitment(repo, change_id="proof-binding")
    return repo, commit_fixture(repo, "bind proof")


def store_proof(root: Path, record: Attestation, *, selected: bool = True) -> None:
    store = proof_artifact_root(root)
    store.mkdir(parents=True, exist_ok=True)
    (store / f"{record.id}.json").write_text(record.canonical_json(), encoding="utf-8")
    if selected:
        record_attestations(root, (record,))


def assert_selected_proof(
    root: Path, head: str, *, selected: Attestation | None = None, gap: str | None = None
) -> None:
    assert proof_attestation(root, head) == selected
    assert proof_gaps(root, head) == ([] if gap is None else [gap])
