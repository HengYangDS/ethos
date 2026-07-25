from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.mutation.proof import executed_proof_record
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.evidence.core import ProofRun
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _commit(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def _write_change_contract(root: Path) -> None:
    carrier = root / "openspec" / "changes" / "proof-binding"
    carrier.mkdir(parents=True)
    (carrier / "contract.toml").write_text(
        """schema_version = 1
id = "change:proof-binding"
intent = "Bind proof to the governed change."
subjects = ["repository:self"]
scope = ["**"]
permissions = ["repository.read"]
""",
        encoding="utf-8",
    )


def _adopted_repo(path: Path) -> tuple[Path, str]:
    repo = init_git_repo(path)
    adoption_plan(repo, apply=True)
    _write_change_contract(repo)
    return repo, _commit(repo, "adopt and bind proof")


def _evidence(head: str, action_id: str = "proof") -> dict[str, object]:
    run = ProofRun(
        action_id=action_id,
        command=("true",),
        exit_code=0,
        stdout="",
        stderr="",
        state="proven",
        evidence_class="test",
        verdict="passed",
        trust_bearing=True,
        diagnostics=(),
    )
    return EvidenceSet.from_runs(evidence_id="proof", head=head, runs=(run,)).to_dict()


def test_proof_plan_binds_contract_facts_and_gate_policy(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")

    plan = proof_plan(repo, head=head)

    assert plan.contract_digest
    assert plan.facts_digest
    assert plan.policy_digest
    assert plan.to_dict()["inputs"] == {
        "contract": plan.contract_digest,
        "facts": plan.facts_digest,
        "policy": plan.policy_digest,
    }
    assert plan.permissions == ("repository.read",)


def test_proof_plan_rejects_a_change_for_another_repository(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    contract = repo / "openspec" / "changes" / "proof-binding" / "contract.toml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace(
            'subjects = ["repository:self"]',
            'subjects = ["repository:foreign"]',
        ),
        encoding="utf-8",
    )
    head = _commit(repo, "bind foreign repository")

    assert proof_plan(repo, head=head).gaps() == ("repository_subject_mismatch",)


def test_proof_plan_identity_is_stable_across_linked_worktrees(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    linked = tmp_path / "repo-linked"
    subprocess.run(
        ["git", "worktree", "add", "--detach", linked.as_posix(), head],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )

    assert proof_plan(repo, head=head).digest() == proof_plan(linked, head=head).digest()


def test_proof_plan_identity_changes_with_contract_head_or_policy(tmp_path: Path) -> None:
    repo, first_head = _adopted_repo(tmp_path / "repo")
    first = proof_plan(repo, head=first_head)

    contract = repo / "openspec" / "changes" / "proof-binding" / "contract.toml"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace(
            "Bind proof to the governed change.",
            "Bind the revised proof to the governed change.",
        ),
        encoding="utf-8",
    )
    contract_head = _commit(repo, "revise contract")
    contract_changed = proof_plan(repo, head=contract_head)

    gates = repo / "system" / "gates.toml"
    gates.parent.mkdir()
    gates.write_text("[proof_sets]\nproduct_default = []\n", encoding="utf-8")
    policy_head = _commit(repo, "revise policy")
    policy_changed = proof_plan(repo, head=policy_head)

    assert len({first.digest(), contract_changed.digest(), policy_changed.digest()}) == 3


def test_record_executed_proof_requires_the_exact_executed_plan(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")

    with pytest.raises(ValueError, match="proof_plan_digest_required"):
        record_executed_proof(
            repo,
            {
                "id": "proof",
                "head": head,
                "durability": "local",
                "runs": [],
            },
        )


def test_record_executed_proof_rejects_a_blocked_plan(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    blocked = proof_plan(repo, head=head).model_copy(
        update={"validation_issues": ("repository_subject_mismatch",)}
    )

    with pytest.raises(ValueError, match="proof_plan_not_admitted"):
        record_executed_proof(repo, _evidence(head), plan=blocked)


def test_recorded_proof_rejects_a_forged_plan_digest(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    path = record_executed_proof(
        repo,
        _evidence(head),
        plan=proof_plan(repo, head=head),
    )
    assert executed_proof_record(repo, head) is not None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["plan_digest"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert executed_proof_record(repo, head) is None


def test_recorded_proof_never_merges_evidence_from_a_different_plan(tmp_path: Path) -> None:
    repo, head = _adopted_repo(tmp_path / "repo")
    first = proof_plan(repo, head=head)
    second = first.model_copy(update={"policy_digest": "f" * 64})

    record_executed_proof(repo, _evidence(head, "first"), plan=first)
    with pytest.raises(ValueError, match="proof_plan_binding_mismatch"):
        record_executed_proof(repo, _evidence(head, "second"), plan=second)

    record = executed_proof_record(repo, head)
    assert record is not None
    assert [run["action_id"] for run in record["evidence"]["runs"]] == ["first"]


def test_record_executed_proof_rejects_a_plan_for_another_head(tmp_path: Path) -> None:
    repo, first_head = _adopted_repo(tmp_path / "repo")
    first = proof_plan(repo, head=first_head)
    (repo / "NEXT.md").write_text("next\n", encoding="utf-8")
    second_head = _commit(repo, "next")

    with pytest.raises(ValueError, match="proof_plan_head_mismatch"):
        record_executed_proof(repo, _evidence(second_head), plan=first)
