from __future__ import annotations

import json
import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.accepted as accepted_mutation
import ethos.adapters.mutation.landing as landing_mutation
import ethos.adapters.openspec.cli as openspec_cli
import ethos.surface.cli.root.proof as proof_cli
import ethos.surface.cli.root.publish as publish_cli
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_plan
from ethos.contracts.plan import proof_effect_digest
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.governed_repository import lane_start_arguments
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.governed_repository import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def _archive_fixture_change(
    monkeypatch: pytest.MonkeyPatch,
    worktree: Path,
) -> str:
    """Archive the fixture Change through the official OpenSpec CLI and advance its Lease."""
    completed_head = commit_fixture_file(
        worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete fixture change",
    )
    archive_command = openspec_base_command()
    assert archive_command is not None
    archive = subprocess.run(
        [*archive_command, "archive", "fixture-change", "--yes", "--json"],
        cwd=worktree,
        text=True,
        capture_output=True,
        check=False,
    )
    assert archive.returncode == 0, archive.stderr
    git(worktree, "add", ".")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "archive fixture change",
    )
    archived_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook = run_ethos(
        "hook",
        "ref-transaction",
        f"refs/heads/{git(worktree, 'branch', '--show-current')}",
        completed_head,
        archived_head,
        "--phase",
        "committed",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert hook["verdict"] == "pass"
    return archived_head


def test_land_dry_run_reports_dirty_work_lane_gap(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    worktree = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, worktree), cwd=repo)
    (worktree / "README.md").write_text("# dirty\n", encoding="utf-8")
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "work_lane_dirty" in payload["required_gaps"]


def test_land_blocks_completed_active_openspec_change_before_candidate_landing(
    tmp_path: Path, monkeypatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    worktree = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, worktree), cwd=repo)

    def fake_audit(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
        assert openspec_mode == "shape"
        return {"verdict": "pass", "required_gaps": [], "root": root.as_posix()}

    monkeypatch.setattr("ethos.domain.status.audit_for_root", fake_audit)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda *_args: {
            "command": ["openspec", "list", "--json"],
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": {
                "changes": [
                    {
                        "name": "sample-change",
                        "completedTasks": 1,
                        "totalTasks": 1,
                        "status": "complete",
                    }
                ]
            },
            "parse_error": "",
        },
    )
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["completed_changes"] == ["sample-change"]


def test_land_dry_run_reports_stale_candidate_base_with_refresh_action(
    monkeypatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    candidate_head = git(candidate, "rev-parse", "HEAD")
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["candidate_base_stale"]
    assert payload["next_action"] == (
        f"ethos lane refresh-base --apply --authorize --expect-head {work_head} --json"
    )
    assert payload["data"]["candidate_update"] == {
        "verdict": "block",
        "state": "blocked",
        "branch": "candidate/dev",
        "head": work_head,
        "candidate_head": candidate_head,
        "path": candidate.as_posix(),
        "required_gaps": ["candidate_base_stale"],
        "remediation": [
            {
                "gap": "candidate_base_stale",
                "kind": "stale_base",
                "next_action": (
                    "ethos lane refresh-base --apply --authorize --expect-head <head> --json"
                ),
            }
        ],
    }


def test_land_dry_run_requires_executed_proof_before_ready_state(
    monkeypatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["proof_not_proven"]
    assert payload["next_action"] == f"ethos prove --execute --expect-head {work_head} --json"
    assert "proof_readiness" not in payload["data"]


def test_land_blocks_active_change_even_when_exact_head_is_proven(tmp_path: Path) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = git(worktree, "rev-parse", "HEAD")
    seed_executed_proof(worktree, work_head)
    payload = run_ethos("land", "--root", worktree.as_posix(), "--json", cwd=worktree)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [
        "openspec_active_change_unarchived:fixture-change:work_lane"
    ]
    assert payload["next_action"] == (
        "ethos lane archive-change --change fixture-change "
        f"--expect-head {work_head} --apply --json"
    )
    assert "proof_readiness" not in payload["data"]
    mutation = payload["data"]["mutation"]
    assert mutation["request"] == {
        "command": "land",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert mutation["decision"]["verdict"] == "block"
    assert mutation["decision"]["subject"]["action"] == "candidate.integrate"
    expected_state = mutation["decision"]["subject"]["expected_state"]
    assert expected_state["source_head"] == work_head
    assert expected_state["source_ref"] == "refs/heads/work/feature"
    assert expected_state["target_ref"] == "refs/heads/candidate/dev"
    assert expected_state["holder_ref"] == "agent:test:case:agent-test"
    assert expected_state["lease_id"].startswith("lease:")
    assert expected_state["lease_epoch"] == 1
    assert mutation["decision"]["required_gaps"] == payload["required_gaps"]
    assert mutation["decision"]["mints_authority"] is False
    assert "authorized" not in mutation


def test_land_apply_refuses_active_change_without_updating_candidate(tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(worktree, work_head)

    payload = run_ethos_blocked(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [
        "openspec_active_change_unarchived:fixture-change:work_lane"
    ]
    assert payload["next_action"] == (
        "ethos lane archive-change --change fixture-change "
        f"--expect-head {work_head} --apply --json"
    )
    assert payload["data"]["candidate_update"] == {}
    assert git(candidate, "rev-parse", "HEAD") == candidate_head


def test_land_allows_officially_archived_work_lane_head(monkeypatch, tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    archived_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, archived_head)
    payload = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        archived_head,
        "--json",
        cwd=worktree,
    )

    assert payload["verdict"] == "pass"
    assert payload["state"] == "candidate_validated"
    assert payload["required_gaps"] == []
    proof = proof_attestation(worktree, archived_head)
    assert proof is not None
    assert payload["data"]["candidate_update"]["attestation"]["statement"]["plan"][
        "prior_attestations"
    ] == {"proof": proof.model_dump(mode="json")}
    assert git(candidate, "rev-parse", "HEAD") == archived_head


def test_work_lane_proof_is_invalid_after_same_head_lease_handoff(
    monkeypatch, tmp_path: Path
) -> None:
    holder = "agent:test:case:agent-test"
    successor = "agent:test:case:successor"
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path, holder_ref=holder)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    head = _archive_fixture_change(monkeypatch, worktree)
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    seed_executed_proof(worktree, head)
    assert proof_attestation(worktree, head) is not None
    assert proof_gaps(worktree, head) == []
    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    offer = apply_lease_operation(
        state_database(worktree),
        request=LeaseOperationRequest(
            operation="handoff_offer",
            branch=branch,
            holder_ref=holder,
            target_holder_ref=successor,
            lease_id=str(lease["lease_id"]),
            expected_epoch=int(lease["epoch"]),
            expect_head=head,
            expected_expires_at=str(lease["expires_at"]),
            expected_payload_sha256=str(lease["payload_sha256"]),
            apply=True,
        ),
    )
    accepted = apply_lease_operation(
        state_database(worktree),
        request=LeaseOperationRequest(
            operation="handoff_accept",
            branch=branch,
            holder_ref=holder,
            target_holder_ref=successor,
            offer_id=str(offer["offer_id"]),
            lease_id=str(offer["lease_id"]),
            expected_epoch=int(offer["epoch"]),
            expect_head=head,
            expected_expires_at=str(offer["expires_at"]),
            expected_payload_sha256=str(offer["payload_sha256"]),
            holder_quiesced=True,
            apply=True,
        ),
    )
    assert (accepted["holder_ref"], accepted["epoch"]) == (successor, int(lease["epoch"]) + 1)

    assert proof_attestation(worktree, head) is None
    assert proof_gaps(worktree, head) == ["proof_lease_generation_stale"]
    assert proof_attestation(candidate, head) is None
    assert proof_gaps(candidate, head) == ["proof_lease_generation_stale"]


@pytest.mark.parametrize(
    ("lease_state", "commitment_binding"),
    [("expired", "expired"), ("unknown", "unknown"), ("valid", "mismatch")],
)
def test_work_lane_proof_requires_a_live_commitment_bound_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lease_state: str,
    commitment_binding: str,
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, head)
    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    monkeypatch.setattr(
        "ethos.adapters.mutation.proof_admission.leases_by_branch",
        lambda _root: {
            branch: lease
            | {
                "lease_state": lease_state,
                "commitment_binding": commitment_binding,
            }
        },
    )

    assert proof_attestation(worktree, head) is None
    assert proof_gaps(worktree, head) == ["proof_lease_generation_stale"]


def test_land_allows_full_proof_for_lease_bound_authority(monkeypatch, tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(
        worktree,
        "system/gates.toml",
        'schema_version = 1\nid = "fixture-gates"\n\n'
        '[proof_sets]\ndefault = ["sample-tests", "sample-static"]\n'
        'full = ["sample-tests", "sample-static", "full-only"]\n\n'
        '[[gates]]\nid = "sample-tests"\nregistries = ["runtime"]\n'
        'kind = "test"\ncommand = ["sample", "test"]\n'
        'asset_classes = ["python-code"]\n'
        'dimensions = ["test", "coverage"]\nevidence_class = "proof"\n'
        'trust_bearing = true\ntool_adapter = "fixture"\n\n'
        '[[gates]]\nid = "sample-static"\nregistries = ["runtime"]\n'
        'kind = "typing"\ncommand = ["sample", "typecheck"]\n'
        'asset_classes = ["python-code"]\n'
        'dimensions = ["static-analysis"]\nevidence_class = "contract"\n'
        'trust_bearing = true\ntool_adapter = "fixture"\n\n'
        '[[gates]]\nid = "full-only"\nregistries = ["runtime"]\n'
        'kind = "test"\ncommand = ["sample", "full"]\n'
        'asset_classes = ["python-code"]\n'
        'dimensions = ["behavior"]\nevidence_class = "proof"\n'
        'trust_bearing = true\ntool_adapter = "fixture"\n',
        "declare split proof floors",
    )
    commit_fixture_file(
        worktree,
        ".ethos/profile.toml",
        'profile_id = "repo"\n\n'
        '[proof]\ngate_registry = "system/gates.toml"\n\n'
        '[openspec]\nmaterial_paths = ["openspec/**"]\n',
        "select split proof floors",
    )
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    archived_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, archived_head, full=True)
    monkeypatch.setattr(
        "ethos.domain.status.audit_for_root",
        lambda root, **_: {
            "verdict": "pass",
            "required_gaps": [],
            "root": root.as_posix(),
        },
    )

    payload = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        archived_head,
        "--json",
        cwd=worktree,
    )

    assert payload["verdict"] == "pass"
    assert payload["state"] == "candidate_validated"
    assert payload["required_gaps"] == []
    assert git(candidate, "rev-parse", "HEAD") == archived_head


def test_land_rejects_proof_self_granted_candidate_authority(monkeypatch, tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(worktree, work_head)
    valid = proof_attestation(worktree, work_head)
    assert valid is not None
    plan = TransitionPlan.model_validate(valid.model_dump(mode="json")["statement"]["plan"])
    commitment = dict(valid.statement["commitment"])
    commitment["permissions"] = [
        *commitment["permissions"],
        "git.ref.update:refs/heads/candidate/dev",
    ]
    commitment_digest = Commitment.model_validate_json(json.dumps(commitment)).digest()
    assert commitment_digest != valid.commitment_digest
    fact_values = dict(plan.facts["values"])
    fact_values["changed_paths"] = ()
    facts = Facts.model_validate(
        {
            **plan.facts,
            "observed_at": datetime.now(UTC),
            "values": fact_values,
        }
    )
    effect_digest = proof_effect_digest(
        commitment=commitment_digest,
        facts=facts.digest(),
        policy=plan.inputs.policy,
        nodes=plan.nodes,
    )
    forged_plan = TransitionPlan.compile(
        inputs=PlanInputs(
            commitment=commitment_digest,
            facts=facts.digest(),
            prior_attestations=plan.inputs.prior_attestations,
            policy=plan.inputs.policy,
            effect=effect_digest,
        ),
        closure={
            "commitment": commitment,
            "prior_attestations": plan.prior_attestations,
            "policy": valid.statement["policy"],
            "effect": {
                "operation": "proof.execute",
                "commitment": commitment_digest,
                "facts": facts.digest(),
                "policy": plan.inputs.policy,
                "nodes": [node.model_dump(mode="json") for node in plan.nodes],
            },
        },
        permissions=tuple(commitment["permissions"]),
        facts=facts.model_dump(mode="json", exclude={"observed_at"}),
        nodes=plan.nodes,
    )
    forged = Attestation.issue(
        valid.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
        | {
            "commitment_digest": commitment_digest,
            "facts_digest": facts.digest(),
            "plan_digest": forged_plan.digest,
            "effect_digest": effect_digest,
            "statement": valid.statement
            | {
                "changed_paths": (),
                "inputs": {
                    "commitment": commitment_digest,
                    "facts": facts.digest(),
                    "plan": forged_plan.digest,
                    "policy": plan.inputs.policy,
                    "effect": effect_digest,
                },
                "plan": forged_plan.model_dump(mode="json"),
                "commitment": commitment,
            },
        }
    )
    (attestation_store_dir(worktree) / f"{valid.id}.json").unlink()
    persist_proof_attestation(worktree, forged)
    assert proof_attestation(worktree, work_head) == forged

    payload = run_ethos_blocked(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert payload["required_gaps"] == ["proof_attestation_authority_binding_mismatch"]
    assert git(candidate, "rev-parse", "HEAD") == candidate_head


def test_lane_refresh_base_apply_rebases_stale_work_lane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    commit_fixture_file(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    previous_head = git(worktree, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    git(worktree, "config", "commit.gpgsign", "true")
    git(worktree, "config", "user.signingkey", "missing-test-signing-key")
    payload = run_ethos(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous_head,
        "--json",
        cwd=worktree,
    )
    refreshed_head = git(worktree, "rev-parse", "HEAD")
    assert payload["verdict"] == "pass"
    assert payload["state"] == "base_refreshed"
    assert payload["required_gaps"] == []
    assert payload["next_action"] == "ethos land --json"
    assert payload["data"]["branch"] == "work/feature"
    assert payload["data"]["previous_head"] == previous_head
    assert payload["data"]["head"] == refreshed_head
    assert payload["data"]["candidate_head"] == candidate_head
    assert refreshed_head != previous_head
    assert payload["data"]["rebase_attestation"]["predicate"] == "effect:git-rebase"
    assert payload["data"]["attachment_attestation"]["predicate"] == "effect:git-worktree"


def test_lane_refresh_base_conflict_returns_block_instead_of_type_error(tmp_path: Path) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(candidate, "CONFLICT.txt", "candidate\n", "advance candidate")
    previous_head = commit_fixture_file(worktree, "CONFLICT.txt", "work lane\n", "conflict")

    completed = run_ethos_raw(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous_head,
        "--json",
        cwd=worktree,
    )
    assert completed.returncode == 1, completed.stderr
    payload = json.loads(completed.stdout)

    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "ok" not in payload
    assert "refresh_base_failed" in payload["required_gaps"]
    assert git(worktree, "branch", "--show-current") == "work/feature"


def test_land_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    payload = run_ethos_blocked("land", "--apply", "--json", cwd=repo)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]
    mutation = payload["data"]["mutation"]
    assert mutation["request"]["confirmation_present"] is False
    assert mutation["decision"]["verdict"] == "block"
    assert mutation["decision"]["required_gaps"] == payload["required_gaps"]
    assert "decision" not in {
        key: value for key, value in mutation.items() if isinstance(value, str)
    }


def test_cli_runner_rejects_implicit_apply_against_repository_checkout() -> None:
    args = ("land", "--apply", "--json")
    with pytest.raises(AssertionError, match="--apply calls must pass cwd"):
        run_ethos_blocked(*args)


@pytest.mark.parametrize("command", ["land", "publish"])
def test_apply_rejects_accepted_root_even_when_authorized(tmp_path: Path, command: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    payload = run_ethos_blocked(
        command, "--apply", "--authorize", "--expect-head", head, "--json", cwd=repo
    )
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "protected_root_mutation" in payload["required_gaps"]


def test_publish_dry_run_remains_available_on_accepted_root_after_land_boundary(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    payload = run_ethos("publish", "--json", cwd=repo)
    assert payload["verdict"] == "pass"
    assert payload["state"] == "local_publish_ready"
    assert payload["required_gaps"] == []
    mutation = payload["data"]["mutation"]
    assert mutation["request"] == {
        "command": "publish",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert mutation["decision"]["verdict"] == "unknown"
    assert mutation["decision"]["subject"]["action"] == "remote.publish"
    assert mutation["decision"]["required_gaps"] == []
    assert mutation["decision"]["next_action"]
    expected_state = mutation["decision"]["subject"]["expected_state"]
    assert expected_state["source_ref"] == "refs/heads/dev"
    assert expected_state["source_head"] == head
    assert expected_state["target_ref"] == "refs/heads/dev"
    assert expected_state["remote"] == "origin"
    assert expected_state["remote_availability_state"] in {
        "unconfigured",
        "unavailable",
        "not_probed",
    }
    assert mutation["decision"]["decision_basis"]["identity_basis"] == "not_evaluated"


def test_publish_blocks_exact_head_proof_gap_without_parallel_quality_verdict(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    gap = "proof_attestation_stale:quality-policy"
    monkeypatch.setattr(publish_cli, "repository_context", lambda _repo: {"profile": "test"})
    monkeypatch.setattr(
        publish_cli,
        "proof_gaps",
        lambda _repo, _head, **_kwargs: [gap],
    )
    payload = run_ethos("publish", "--json", cwd=repo)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == [gap]
    assert payload["summary"]["local_readiness"] is False
    assert "hard_quality_floor" not in payload["data"]


def test_publish_apply_defers_when_remote_transition_is_not_performed(
    monkeypatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    lease_head = git(worktree, "rev-parse", "HEAD")
    head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook = run_ethos(
        "hook",
        "ref-transaction",
        "refs/heads/work/feature",
        lease_head,
        head,
        "--phase",
        "committed",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert hook["verdict"] == "pass"
    seed_executed_proof(worktree, head)
    payload = run_ethos_blocked(
        "publish", "--apply", "--authorize", "--expect-head", head, "--json", cwd=worktree
    )
    assert payload["verdict"] == "unknown"
    assert payload["state"] == "publication_deferred"
    assert payload["required_gaps"] == []
    assert payload["summary"]["local_readiness"] is True
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"


@pytest.mark.parametrize(
    "arguments",
    [
        ("origin", "ssh://git@example.invalid/group/repo.git"),
        ("unexpected",),
    ],
    ids=("hidden-pre-push", "non-hook"),
)
def test_publish_rejects_positional_arguments(tmp_path: Path, arguments: tuple[str, ...]) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    assert run_ethos_raw("publish", "--json", *arguments, cwd=repo).returncode != 0


def test_publish_dry_run_blocks_release_root_active_openspec_residue(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    git(repo, "checkout", "-b", "main")
    leak = repo / "openspec" / "changes" / "release-leak"
    leak.mkdir(parents=True)
    (leak / "proposal.md").write_text("# release leak\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "leak active openspec carrier on release root",
    )
    git(repo, "checkout", "dev")
    payload = run_ethos("publish", "--json", cwd=repo)
    gap = "openspec_protected_branch_active_change_unarchived:main:release_root:release-leak"
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert gap in payload["required_gaps"]
    assert payload["data"]["release_root_open_spec"] == {"required_gaps": [gap], "blocking": True}


def _prepare_configured_branch_roles(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    git(repo, "branch", "integration", "dev")
    git(repo, "checkout", "integration")
    write_role_policy(
        repo,
        release_branch="release",
        accepted_branch="integration",
        candidate_branch="stage/integration",
        work_branch_prefix="lane/",
        proposal_branch_prefix="review/",
        release_mirror="accepted_ff",
    )
    git(repo, "branch", "release", "integration")
    accepted_head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, accepted_head)
    candidate_path = tmp_path / "repo-stage-integration"
    candidate_payload = run_ethos(
        "lane",
        "candidate",
        "--root",
        repo.as_posix(),
        "--path",
        candidate_path.as_posix(),
        "--expect-head",
        accepted_head,
        "--apply",
        "--json",
        cwd=repo,
    )
    assert candidate_payload["verdict"] == "pass"
    assert candidate_payload["data"]["branch"] == "stage/integration"
    assert candidate_payload["data"]["path"] == candidate_path.as_posix()
    worktree = tmp_path / "repo-lane-configured"
    start_payload = run_ethos(*lane_start_arguments(repo, worktree, name="configured"), cwd=repo)
    assert start_payload["verdict"] == "pass"
    assert start_payload["data"]["branch"] == "lane/configured"
    assert start_payload["data"]["base"] == "stage/integration"
    assert start_payload["summary"] == {
        "branch": "lane/configured",
        "path": worktree.resolve().as_posix(),
    }
    return repo, candidate_path, worktree, accepted_head


def _commit_configured_lane(monkeypatch, worktree: Path) -> str:
    lease_head = git(worktree, "rev-parse", "HEAD")
    (worktree / "README.md").write_text("# configured lane\n", encoding="utf-8")
    git(worktree, "add", "README.md")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configured lane change",
    )
    work_head = git(worktree, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook_payload = run_ethos(
        "hook",
        "ref-transaction",
        "refs/heads/lane/configured",
        lease_head,
        work_head,
        "--phase",
        "committed",
        "--root",
        worktree.as_posix(),
        "--json",
        cwd=worktree,
    )
    assert hook_payload["verdict"] == "pass"
    work_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, work_head)
    return work_head


def _assert_configured_publish(payload: dict[str, object]) -> None:
    assert payload["verdict"] == "pass"
    assert payload["summary"]["mode"] == "local_readiness"
    assert payload["summary"]["local_readiness"] is True
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["summary"]["remote_publication_state"] == "deferred"
    assert payload["summary"]["hosted_ci_status_claimed"] is False
    assert payload["summary"]["proposal_branch"] == "review/configured"
    assert payload["data"]["publication"]["proposal_branch"] == "review/configured"
    local_proposal = payload["data"]["publication"]["local_proposal_package"]
    assert local_proposal["kind"] == "proposal_branch_plan"
    assert local_proposal["source_branch"] == "lane/configured"
    assert local_proposal["proposal_branch"] == "review/configured"
    assert local_proposal["remote_push"] == "not_performed"
    assert local_proposal["remote_state"] == "deferred"
    assert payload["data"]["publication"]["remote_state"] == "deferred"
    assert local_proposal["blocking"] is False
    assert local_proposal["remote_availability"]["blocking"] is False
    assert local_proposal["local_ci_fallback"]["kind"] == "local_ci_fallback"
    assert local_proposal["local_ci_fallback"]["hosted_ci_status_claimed"] is False
    assert local_proposal["required_steps"] == [
        "land work lane to candidate role",
        "fast-forward accepted root from candidate role",
        "run local-ci fallback when remote publication is unavailable",
        "create configured proposal branch when remote publication is available",
    ]


def _land_configured_lane(
    repo: Path,
    candidate_path: Path,
    worktree: Path,
    accepted_head: str,
    work_head: str,
) -> None:
    land_payload = run_ethos(
        "land", "--apply", "--authorize", "--expect-head", work_head, "--json", cwd=worktree
    )
    assert land_payload["verdict"] == "pass"
    assert land_payload["data"]["candidate_update"]["branch"] == "stage/integration"
    candidate_attestation = land_payload["data"]["candidate_update"]["attestation"]
    assert candidate_attestation["predicate"] == "effect:git-ref-update"
    assert not {"kind", "content", "mints_authority"} & set(candidate_attestation)
    proof = proof_attestation(worktree, work_head)
    assert proof is not None
    prior_attestations = {"proof": proof.model_dump(mode="json")}
    assert candidate_attestation["statement"]["plan"]["prior_attestations"] == prior_attestations
    assert git(candidate_path, "rev-parse", "HEAD") == work_head
    assert git(repo, "rev-parse", "integration") == accepted_head
    closeout_payload = run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )
    assert closeout_payload["verdict"] == "pass"
    accepted_update = closeout_payload["data"]["accepted_update"]
    assert accepted_update["verdict"] == "pass"
    assert accepted_update["state"] == "accepted_validated"
    assert accepted_update["branch"] == "integration"
    assert accepted_update["source_branch"] == "stage/integration"
    assert accepted_update["head"] == work_head
    assert accepted_update["previous_head"] == accepted_head
    assert accepted_update["required_gaps"] == []
    accepted_attestation = accepted_update["attestation"]
    assert accepted_attestation["predicate"] == "effect:git-ref-update"
    assert (
        accepted_attestation["commitment_digest"]
        == load_repository_commitment(repo, tree_ref=accepted_head).digest()
    )
    assert accepted_attestation["statement"]["plan"]["prior_attestations"] == prior_attestations
    assert accepted_attestation["statement"]["result"]["state"] == "applied"
    assert not {"kind", "content", "mints_authority"} & set(accepted_attestation)
    assert git(repo, "rev-parse", "release") == work_head


def test_closeout_rejects_candidate_self_granted_accepted_authority(tmp_path: Path) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    repository_commitment = repo / ".ethos" / "commitment.toml"
    repository_commitment.write_text(
        repository_commitment.read_text(encoding="utf-8").replace(
            ', "git.ref.compare-and-swap"', ""
        ),
        encoding="utf-8",
    )
    git(repo, "add", repository_commitment.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "remove accepted update authority",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted_head)
    candidate_commitment = candidate / ".ethos" / "commitment.toml"
    candidate_commitment.write_text(
        candidate_commitment.read_text(encoding="utf-8").replace(
            'permissions = ["repository.read"]',
            'permissions = ["repository.read", "git.ref.compare-and-swap"]',
        ),
        encoding="utf-8",
    )
    git(candidate, "add", candidate_commitment.as_posix())
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "self grant accepted update authority",
    )
    candidate_head = git(candidate, "rev-parse", "HEAD")
    git(repo, "branch", "candidate-selected-accepted", accepted_head)
    seed_executed_proof(candidate, candidate_head)

    report = accepted_mutation.promote_candidate(
        root=repo,
        policy=load_branch_role_policy(repo),
        current_head=accepted_head,
        candidate_head=candidate_head,
        status=workspace_status(repo),
    )

    assert report["verdict"] == "block", report
    assert report["required_gaps"] == ["accepted_atomic_update_rejected"]
    assert "git_effect_permission_denied" in report["stderr"]
    assert git(repo, "rev-parse", "dev") == accepted_head


def test_closeout_bootstraps_the_first_repository_commitment_from_an_authorized_candidate(
    tmp_path: Path,
) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    commitment_text = (repo / ".ethos" / "commitment.toml").read_text(encoding="utf-8")
    git(repo, "rm", ".ethos/commitment.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "represent the pre-commitment accepted root",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted_head)
    (candidate / ".ethos" / "commitment.toml").write_text(commitment_text, encoding="utf-8")
    git(candidate, "add", ".ethos/commitment.toml")
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "introduce the first repository commitment",
    )
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, candidate_head)

    report = accepted_mutation.promote_candidate(
        root=repo,
        policy=load_branch_role_policy(repo),
        current_head=accepted_head,
        candidate_head=candidate_head,
        status=workspace_status(repo),
    )

    assert report["verdict"] == "pass", json.dumps(report, indent=2)
    assert report["previous_head"] == accepted_head
    assert report["head"] == candidate_head
    assert git(repo, "rev-parse", "dev") == candidate_head
    assert (
        report["attestation"]["commitment_digest"]
        == load_repository_commitment(repo, tree_ref=candidate_head).digest()
    )


def test_closeout_first_cas_uses_the_accepted_policy_when_candidate_changes_topology(
    tmp_path: Path,
) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    accepted_head = git(repo, "rev-parse", "HEAD")
    workspace = candidate / ".ethos" / "workspace.toml"
    workspace.parent.mkdir(parents=True, exist_ok=True)
    workspace.write_text(
        """[branch_roles]
release_branch = "main"
accepted_branch = "candidate-selected-accepted"
candidate_branch = "candidate/dev"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"
release_mirror = "independent"
repository_family_worktrees = false
""",
        encoding="utf-8",
    )
    git(candidate, "add", workspace.as_posix())
    git(
        candidate,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "change future branch topology",
    )
    candidate_head = git(candidate, "rev-parse", "HEAD")
    git(repo, "branch", "candidate-selected-accepted", accepted_head)
    seed_executed_proof(candidate, candidate_head)

    report = landing_mutation.apply_candidate_to_accepted(
        root=repo,
        authorized=True,
        expect_head=accepted_head,
    )

    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == candidate_head
    assert git(repo, "rev-parse", "candidate-selected-accepted") == accepted_head


def test_closeout_uses_default_policy_when_profile_has_no_workspace(tmp_path: Path) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    git(repo, "rm", ".ethos/workspace.toml")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "use default branch roles",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted_head)
    assert (repo / ".ethos/profile.toml").is_file()
    assert not (repo / ".ethos/workspace.toml").exists()
    candidate_head = commit_fixture_file(candidate, "README.md", "# candidate\n", "candidate")
    seed_executed_proof(candidate, candidate_head)

    report = landing_mutation.apply_candidate_to_accepted(
        root=repo,
        authorized=True,
        expect_head=accepted_head,
    )

    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == candidate_head


def test_closeout_rejects_an_explicit_incomplete_workspace(tmp_path: Path) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    workspace.write_text('[branch_roles]\naccepted_branch = "dev"\n', encoding="utf-8")
    git(repo, "add", workspace.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "record incomplete branch roles",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted_head)

    report = landing_mutation.apply_candidate_to_accepted(
        root=repo,
        authorized=True,
        expect_head=accepted_head,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["accepted_policy_unavailable"]


def test_closeout_uses_committed_accepted_policy_when_worktree_masks_release_mirror(
    tmp_path: Path,
) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    workspace = repo / ".ethos" / "workspace.toml"
    workspace.write_text(
        workspace.read_text(encoding="utf-8").replace(
            'release_mirror = "independent"', 'release_mirror = "accepted_ff"'
        ),
        encoding="utf-8",
    )
    git(repo, "add", workspace.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "require release mirror",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "main", accepted_head)
    git(candidate, "reset", "--hard", accepted_head)
    workspace.write_text(
        workspace.read_text(encoding="utf-8").replace(
            'release_mirror = "accepted_ff"', 'release_mirror = "independent"'
        ),
        encoding="utf-8",
    )
    git(repo, "update-index", "--skip-worktree", ".ethos/workspace.toml")
    candidate_head = commit_fixture_file(candidate, "README.md", "# candidate\n", "candidate")
    seed_executed_proof(candidate, candidate_head)

    report = landing_mutation.apply_candidate_to_accepted(
        root=repo,
        authorized=True,
        expect_head=accepted_head,
    )

    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == candidate_head
    assert git(repo, "rev-parse", "main") == candidate_head


def _retire_configured_lane(repo: Path, work_head: str) -> None:
    blocked = run_ethos_blocked(
        "lane",
        "retire",
        "landed",
        "--branch",
        "lane/configured",
        "--expect-head",
        work_head,
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    assert blocked["required_gaps"] == ["authorization_required"]
    assert git(repo, "rev-parse", "lane/configured") == work_head
    retire_payload = run_ethos(
        "lane",
        "retire",
        "landed",
        "--branch",
        "lane/configured",
        "--expect-head",
        work_head,
        "--apply",
        "--authorize",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    assert retire_payload["verdict"] == "pass"
    assert retire_payload["summary"] == {
        "landed_lane_count": 1,
        "selected_branch": "lane/configured",
        "selected_retire_ready": True,
        "selected_blockers": [],
    }
    assert retire_payload["data"]["mutation"]["request"]["expect_head"] == work_head


def test_configured_branch_roles_drive_local_lifecycle_commands(
    monkeypatch, tmp_path: Path
) -> None:
    repo, candidate_path, worktree, accepted_head = _prepare_configured_branch_roles(tmp_path)
    work_head = _commit_configured_lane(monkeypatch, worktree)
    publish_payload = run_ethos("publish", "--json", cwd=worktree)
    _assert_configured_publish(publish_payload)
    _land_configured_lane(repo, candidate_path, worktree, accepted_head, work_head)
    _retire_configured_lane(repo, work_head)


def test_publish_invalid_topology_does_not_infer_origin_remote(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    (repo / ".ethos" / "release.toml").write_text("[publication]\n", encoding="utf-8")

    payload = run_ethos("publish", "--json", cwd=repo)

    assert "publication_topology_gitlab_remote_missing" in payload["required_gaps"]
    expected_state = payload["data"]["mutation"]["decision"]["subject"]["expected_state"]
    assert expected_state["remote"] == ""
    assert [target["remote"] for target in expected_state["remote_targets"]] == ["", ""]


def test_publish_apply_requires_authorization_and_expected_head(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    payload = run_ethos_blocked("publish", "--apply", "--json", cwd=repo)
    assert payload["verdict"] == "block"
    assert payload["state"] == "blocked"
    assert "authorization_required" in payload["required_gaps"]
    assert "expect_head_required" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("evidence_head_kind", "expected_state", "expected_action", "expected_actions"),
    [
        (
            "current",
            "current",
            "remote unavailable; local-ci fallback evidence is current at HEAD",
            ("remote unavailable; local-ci fallback evidence is current at HEAD", "ethos status"),
        ),
        (
            "stale",
            "stale",
            "run uv run --frozen --offline python -m nox -s local_ci as local fallback evidence",
            None,
        ),
    ],
    ids=("current", "stale"),
)
def test_publish_reports_local_ci_fallback_evidence(
    tmp_path: Path,
    evidence_head_kind: str,
    expected_state: str,
    expected_action: str,
    expected_actions: tuple[str, ...] | None,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    evidence_head = head if evidence_head_kind == "current" else "stale-head"
    fallback = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    fallback.parent.mkdir(parents=True)
    fallback.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "ethos_local_ci_fallback_evidence",
                "verdict": "pass",
                "head": evidence_head,
                "command": "uv run --frozen --offline python -m nox -s local_ci",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = run_ethos("publish", "--json", cwd=repo)
    evidence_status = payload["data"]["local_ci_fallback"]["evidence_status"]
    assert evidence_status["state"] == expected_state
    assert evidence_status["current_head"] == head
    assert evidence_status["evidence_head"] == evidence_head
    assert payload["summary"]["next_publication_action"] == expected_action
    if expected_actions is not None:
        assert payload["next_action"] == expected_actions[0]


def test_publish_rejects_legacy_local_ci_ok_without_explicit_verdict(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    fallback = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    fallback.parent.mkdir(parents=True)
    fallback.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "ethos_local_ci_fallback_evidence",
                "ok": True,
                "head": head,
                "command": "uv run --frozen --offline python -m nox -s local_ci",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_ethos("publish", "--json", cwd=repo)
    evidence_status = payload["data"]["local_ci_fallback"]["evidence_status"]

    assert evidence_status["verdict"] == "block"
    assert evidence_status["state"] == "stale"
    assert evidence_status["evidence_head"] == head
    assert evidence_status["next_action"] == (
        "run uv run --frozen --offline python -m nox -s local_ci as local fallback evidence"
    )


def test_publish_blocks_without_exact_head_plan_proof(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)

    payload = run_ethos("publish", "--json", cwd=repo)

    assert payload["verdict"] == "block"
    assert "proof_not_proven" in payload["required_gaps"]


def test_prove_scope_helpers_bind_known_and_unknown_scopes_without_host_claims() -> None:
    known = proof_cli.proof_scope_binding("  docs  ")
    unknown = proof_cli.proof_scope_binding("custom scope")

    assert known["scope"] == "docs"
    assert known["accepted"] is True
    assert known["required_gaps"] == []
    assert unknown["scope"] == "custom scope"
    assert unknown["accepted"] is False
    assert unknown["required_gaps"] == ["unknown_proof_scope:custom scope"]
    assert proof_cli.host_probe_boundary(host=True, probe=False) == {
        "requested": True,
        "host": True,
        "probe": False,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "boundary_recorded",
    }


def test_prove_reports_plan_compile_and_admission_failures_as_public_gaps(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)

    admitted = proof_cli.proof_plan(repo, head=git(repo, "rev-parse", "HEAD"))
    rejected_plan = TransitionPlan.compile(
        inputs=admitted.inputs,
        closure={
            "commitment": admitted.commitment,
            "prior_attestations": admitted.prior_attestations,
            "policy": admitted.policy,
            "effect": admitted.effect,
        },
        permissions=admitted.permissions,
        facts=admitted.facts,
        nodes=admitted.nodes,
        required_gaps=("repository_subject_mismatch",),
    )

    monkeypatch.setattr(proof_cli, "proof_plan", lambda *_args, **_kwargs: rejected_plan)
    rejected = run_ethos_blocked("prove", "--json", cwd=repo)
    assert rejected["required_gaps"] == ["repository_subject_mismatch"]
    assert rejected["next_action"] == "repair the Commitment or repository facts"

    monkeypatch.setattr(
        proof_cli,
        "proof_plan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("change_missing")),
    )
    missing = run_ethos_blocked("prove", "--json", cwd=repo)
    assert missing["required_gaps"] == ["change_missing"]
    assert missing["next_action"] == "ethos adopt"


def test_prove_empty_focused_plan_keeps_host_probe_separate_without_claiming_readiness(
    monkeypatch, tmp_path: Path
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    commitment = load_repository_commitment(repo, tree_ref=head)
    ready_plan = compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=head,
            tree=git(repo, "rev-parse", "HEAD^{tree}"),
            observed_at=datetime.now(UTC),
            values={"changed_paths": ()},
        ),
        (),
        policy={},
    )

    monkeypatch.setattr(
        proof_cli.status_domain,
        "audit_for_root",
        lambda *_args, **_kwargs: {
            "verdict": "pass",
            "required_gaps": [],
            "governance_context": {},
            "openspec": {},
        },
    )
    monkeypatch.setattr(proof_cli, "change_scope_paths_from_status", lambda *_args: ())
    monkeypatch.setattr(
        proof_cli,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {"verdict": "pass", "required_gaps": [], "summary": {}},
    )
    monkeypatch.setattr(proof_cli, "proof_plan", lambda *_args, **_kwargs: ready_plan)
    completed = run_ethos_raw("prove", "--scope", "docs", "--host", "--probe", "--json", cwd=repo)
    assert completed.returncode == 1
    payload = json.loads(completed.stdout)

    assert payload["verdict"] == "unknown"
    assert payload["state"] == "gapped"
    assert payload["summary"]["gate_count"] == 0
    assert payload["summary"]["boundary"] == "focused"
    assert payload["data"]["scope_binding"]["scope"] == "docs"
    assert payload["data"]["host_probe"] == {
        "requested": True,
        "host": True,
        "probe": True,
        "evidence_class": "optional_host_readiness",
        "satisfies_repository_proof": False,
        "truth_boundary": "host-local projection",
        "state": "boundary_recorded",
    }


def test_run_plan_checks_resolves_policy_from_plan_head(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    commitment = Commitment(
        id="repository:test",
        intent="Test one empty proof plan.",
        subjects=("repository:test",),
    )
    plan = compile_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=head,
            tree=git(repo, "rev-parse", "HEAD^{tree}"),
            observed_at=datetime.now(UTC),
            values={"changed_paths": ()},
        ),
        (),
        policy={},
    )
    seen: list[dict[str, object]] = []

    class EmptyPolicy:
        def __init__(self) -> None:
            self.registry: dict[str, object] = {}

    def resolve(*_args, **kwargs):
        seen.append(kwargs)
        return EmptyPolicy()

    monkeypatch.setattr(proof_cli, "resolve_gate_policy", resolve)

    assert proof_cli.run_plan_checks(repo=repo, plan=plan, execute=False) == ([], False)
    assert seen == [{"tree_ref": head, "gate_ids": ()}]


def test_land_reobserves_and_retries_one_transient_candidate_cas_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, work_head)
    original = landing_mutation.execute_git_effect
    original_proof = landing_mutation.proof_attestation
    attempts = 0
    proof_reads = 0

    def record_proof(*args, **kwargs):
        nonlocal proof_reads
        proof_reads += 1
        return original_proof(*args, **kwargs)

    def fail_once(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            message = "git_effect_cas_rejected"
            raise ValueError(message)
        return original(*args, **kwargs)

    monkeypatch.setattr(landing_mutation, "execute_git_effect", fail_once)
    monkeypatch.setattr(landing_mutation, "proof_attestation", record_proof)
    payload = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert attempts == 2
    assert proof_reads == 2
    assert payload["verdict"] == "pass"
    assert payload["data"]["candidate_update"]["cas_attempts"] == 2
    assert git(candidate, "rev-parse", "HEAD") == work_head


def test_land_bounds_repeated_candidate_cas_failure_to_two_attempts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, _candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, work_head)
    attempts = 0

    def always_fail(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        message = "git_effect_cas_rejected"
        raise ValueError(message)

    monkeypatch.setattr(landing_mutation, "execute_git_effect", always_fail)
    payload = run_ethos_blocked(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert attempts == 2
    assert payload["required_gaps"] == ["candidate_cas_retry_exhausted"]
    assert payload["data"]["candidate_update"]["cas_attempts"] == 2


def test_land_reports_stale_candidate_without_overwriting_new_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, work_head)
    original = landing_mutation.execute_git_effect
    attempts = 0

    def advance_candidate_then_fail(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            commit_fixture_file(candidate, "PEER.md", "# peer\n", "peer progress")
            message = "git_effect_cas_rejected"
            raise ValueError(message)
        return original(*args, **kwargs)

    monkeypatch.setattr(landing_mutation, "execute_git_effect", advance_candidate_then_fail)
    payload = run_ethos_blocked(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    candidate_head = git(candidate, "rev-parse", "HEAD")
    assert attempts == 1
    assert payload["required_gaps"] == ["candidate_cas_stale"]
    assert payload["data"]["candidate_update"]["candidate_head"] == candidate_head
    assert payload["data"]["candidate_update"]["cas_attempts"] == 1
    assert candidate_head != work_head
