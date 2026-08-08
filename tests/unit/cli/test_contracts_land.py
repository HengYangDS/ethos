from __future__ import annotations

import json
import sqlite3
import subprocess
from contextlib import closing
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.accepted as accepted_mutation
import ethos.adapters.mutation.landing as landing_mutation
import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.plan import PlanInputs
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import proof_effect_digest
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.governed_repository import lane_start_arguments
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import start_adopted_work_lane

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


def test_land_readiness_and_apply_share_narrow_candidate_effect_authority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    branch = git(fixture.worktree, "branch", "--show-current")
    lease = leases_by_branch(fixture.worktree)[branch]
    carrier = str(lease["base_commitment_path"])
    commitment = fixture.worktree / carrier
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            'permissions = ["git.ref.compare-and-swap"]',
            'permissions = ["repository.read", "work-lane.write"]',
        ),
        encoding="utf-8",
    )
    git(fixture.worktree, "add", carrier)
    previous = git(fixture.worktree, "rev-parse", "HEAD")
    git(
        fixture.worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "bind minimal landing commitment",
    )
    head = git(fixture.worktree, "rev-parse", "HEAD")
    binding = exact_commitment_fields(fixture.worktree, head=head, carrier=carrier)
    state = state_database(fixture.worktree)
    with closing(sqlite3.connect(state)) as connection, connection:
        row = connection.execute(
            "select payload_json from leases where subject = ?",
            (branch,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert payload["expected_head"] == previous
        payload.update(
            expected_head=head,
            expected_tree=binding["expected_tree"],
            base_commitment_bytes_sha256=binding["base_commitment_bytes_sha256"],
            base_commitment_digest=binding["base_commitment_digest"],
        )
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")), branch),
        )
    commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
    archived_head = _archive_fixture_change(monkeypatch, fixture.worktree)
    seed_executed_proof(fixture.worktree, archived_head)

    readiness = run_ethos("land", "--json", cwd=fixture.worktree)

    assert readiness["verdict"] == "pass", readiness
    candidate_plan = readiness["data"]["candidate_update"]
    assert candidate_plan["state"] == "candidate_transition_admitted"
    assert candidate_plan["effect"]["updates"] == {
        "refs/heads/candidate/dev": {
            "expected": git(fixture.candidate, "rev-parse", "HEAD"),
            "desired": archived_head,
        }
    }
    assert candidate_plan["permissions"] == ["repository.read", "work-lane.write"]

    applied = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        archived_head,
        "--json",
        cwd=fixture.worktree,
    )

    assert applied["verdict"] == "pass", applied
    attested_plan = applied["data"]["candidate_update"]["attestation"]["statement"]["plan"]
    assert attested_plan["digest"] == candidate_plan["plan_digest"]
    assert attested_plan["effect"] == candidate_plan["effect"]
    assert git(fixture.candidate, "rev-parse", "HEAD") == archived_head


def test_land_readiness_rejects_wrong_actor_before_candidate_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
    archived_head = _archive_fixture_change(monkeypatch, fixture.worktree)
    seed_executed_proof(fixture.worktree, archived_head)
    candidate_head = git(fixture.candidate, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong-holder")

    payload = run_ethos("land", "--json", cwd=fixture.worktree)

    assert payload["required_gaps"] == ["lease_actor_mismatch"]
    assert git(fixture.candidate, "rev-parse", "HEAD") == candidate_head


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
    commitment = dict(plan.commitment)
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
            "policy": plan.policy,
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
            "statement": valid.statement | {"plan": forged_plan.model_dump(mode="json")},
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
canonical_sibling_worktrees = false
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


def test_land_reobserves_and_retries_one_transient_candidate_cas_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    commit_fixture_file(worktree, "FEATURE.md", "# feature\n", "feature work")
    work_head = _archive_fixture_change(monkeypatch, worktree)
    seed_executed_proof(worktree, work_head)
    original = landing_mutation.execute_candidate_plan
    attempts = 0
    plan_ids: list[int] = []

    def fail_once(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        plan_ids.append(id(args[1]))
        if attempts == 1:
            message = "git_effect_cas_rejected"
            raise ValueError(message)
        return original(*args, **kwargs)

    monkeypatch.setattr(landing_mutation, "execute_candidate_plan", fail_once)
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
    assert len(set(plan_ids)) == 1
    assert payload["verdict"] == "pass"
    assert payload["data"]["candidate_update"]["cas_attempts"] == 2
    assert git(candidate, "rev-parse", "HEAD") == work_head


def test_land_exact_equal_candidate_is_an_idempotent_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _repo, candidate, _source, worktree = start_adopted_work_lane(tmp_path)
    work_head = _archive_fixture_change(monkeypatch, worktree)
    git(candidate, "reset", "--hard", work_head)
    seed_executed_proof(worktree, work_head)

    def mutation_is_a_bug(*_args, **_kwargs):
        message = "equal candidate must not compile a Git mutation"
        raise AssertionError(message)

    monkeypatch.setattr(landing_mutation, "execute_candidate_plan", mutation_is_a_bug)
    payload = run_ethos(
        "land",
        "--apply",
        "--authorize",
        "--expect-head",
        work_head,
        "--json",
        cwd=worktree,
    )

    assert payload["verdict"] == "pass"
    assert payload["state"] == "candidate_current"
    assert payload["data"]["candidate_update"]["attestation"] == {}
    assert payload["data"]["candidate_update"]["cas_attempts"] == 0
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

    monkeypatch.setattr(landing_mutation, "execute_candidate_plan", always_fail)
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
    original = landing_mutation.execute_candidate_plan
    attempts = 0

    def advance_candidate_then_fail(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            commit_fixture_file(candidate, "PEER.md", "# peer\n", "peer progress")
            message = "git_effect_cas_rejected"
            raise ValueError(message)
        return original(*args, **kwargs)

    monkeypatch.setattr(landing_mutation, "execute_candidate_plan", advance_candidate_then_fail)
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
