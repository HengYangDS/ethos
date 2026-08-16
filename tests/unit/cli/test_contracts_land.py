from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.accepted as accepted_mutation
import ethos.adapters.mutation.landing as landing_mutation
import ethos.adapters.openspec.cli as openspec_cli
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
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json
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
from tests.support.literal_cases import literal_case

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures/contracts-land"
FULL_GATES = (FIXTURE_ROOT / "full-gates.toml").read_text()
FULL_PROFILE = (FIXTURE_ROOT / "full-profile.toml").read_text()
CHANGED_TOPOLOGY = (FIXTURE_ROOT / "changed-topology.toml").read_text()


def _archive(monkeypatch: pytest.MonkeyPatch, root: Path) -> str:
    old = commit_fixture_file(
        root,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete fixture change",
    )
    command = openspec_base_command()
    assert command is not None
    completed = subprocess.run(
        [*command, "archive", "fixture-change", "--yes", "--json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    git(root, "add", ".")
    _commit(root, "archive fixture change")
    head = git(root, "rev-parse", "HEAD")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    hook = run_ethos(
        "hook",
        "ref-transaction",
        f"refs/heads/{git(root, 'branch', '--show-current')}",
        old,
        head,
        "--phase",
        "committed",
        "--root",
        root.as_posix(),
        "--json",
        cwd=root,
    )
    assert hook["verdict"] == "pass"
    return head


def _commit(root: Path, message: str) -> None:
    git(
        root,
        "commit",
        "-m",
        message,
    )


def _land(root: Path, head: str | None = None, *, blocked: bool = False) -> dict[str, object]:
    args = ["land"]
    if head is not None:
        args += ["--apply", "--authorize", "--expect-head", head]
    args += ["--json"]
    return (run_ethos_blocked if blocked else run_ethos)(*args, cwd=root)


def test_candidate_transition_carries_exact_terminal_v1_repository_prestate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = init_git_repo(tmp_path / "repo")
    carrier = root / ".ethos" / "commitment.toml"
    carrier.parent.mkdir(parents=True, exist_ok=True)
    carrier.write_text(
        'schema_version = 1\nid = "repository:fixture"\n'
        'intent = "fixture"\nsubjects = ["repository:fixture"]\n'
        'scope = ["**"]\ninvariants = []\nacceptance = []\n'
        'authority_refs = []\npermissions = ["repository.read"]\ndependencies = []\n',
        encoding="utf-8",
    )
    candidate_head = commit_fixture_file(root, ".ethos/commitment.toml", carrier.read_text(), "v1")
    carrier.write_text(
        'schema_version = 2\nid = "repository:fixture"\n'
        'intent = "fixture"\nsubjects = ["repository:fixture"]\n'
        'scope = ["**"]\ninvariants = []\nacceptance = []\nrisks = []\n'
        "authority_refs = []\npredecessors = []\nselected_attestations = []\n"
        "dependencies = []\nhypotheses = []\nfalsifiers = []\nexperiment_protocols = []\n",
        encoding="utf-8",
    )
    head = commit_fixture_file(root, ".ethos/commitment.toml", carrier.read_text(), "v2")
    authority = load_repository_commitment(root)
    proof = type(
        "Proof",
        (),
        {
            "commitment_digest": authority.digest(),
            "model_dump": lambda *_args, **_kwargs: {"predicate": "proof:execution"},
        },
    )()
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        landing_mutation,
        "candidate_base_report",
        lambda **_kwargs: {
            "verdict": "pass",
            "head": head,
            "candidate_head": candidate_head,
            "path": root.as_posix(),
            "required_gaps": [],
        },
    )
    monkeypatch.setattr(landing_mutation, "proof_attestation", lambda *_args: proof)
    monkeypatch.setattr(
        landing_mutation,
        "workspace_status",
        lambda *_args, **_kwargs: {"branch": "work/fixture"},
    )
    monkeypatch.setattr(landing_mutation, "leases_by_branch", lambda _root: {"work/fixture": {}})
    monkeypatch.setattr(
        landing_mutation, "load_lease_bound_commitment", lambda *_a, **_k: authority
    )
    monkeypatch.setattr(
        landing_mutation,
        "compile_observed_git_effect",
        lambda *_args, **kwargs: (
            captured.update(kwargs) or type("Plan", (), {"effect": {}, "digest": "plan"})()
        ),
    )
    monkeypatch.setattr(landing_mutation, "admit_git_effect", lambda *_args, **_kwargs: None)

    report = landing_mutation.candidate_transition_readiness(root=root)

    assert report["verdict"] == "pass"
    policy = captured["policy"]
    assert isinstance(policy, dict)
    assert policy["repository_commitment_bootstrap"] is True
    assert policy["prestate_repository_id"] == "repository:fixture"
    assert policy["prestate_repository_bytes_sha256"]


def _proved_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, full: bool = False):
    fixture = start_adopted_work_lane(tmp_path)
    commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
    head = _archive(monkeypatch, fixture.worktree)
    seed_executed_proof(fixture.worktree, head, full=full)
    return fixture, head


LAND_CASES = literal_case("cli.test_contracts_land:assign:LAND_CASES:0")


def _assert_dirty_land_is_blocked(tmp_path: Path) -> None:
    repo, _ = init_repo_with_candidate(tmp_path)
    root = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, root), cwd=repo)
    (root / "README.md").write_text("# dirty\n")
    payload = _land(root)
    assert (payload["verdict"], payload["state"]) == ("block", "blocked")
    assert "work_lane_dirty" in payload["required_gaps"]


def _assert_completed_change_is_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo, _ = init_repo_with_candidate(tmp_path)
    root = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, root), cwd=repo)
    monkeypatch.setattr(
        "ethos.domain.status.audit_for_root",
        lambda root, openspec_mode="shape": (
            {"verdict": "pass", "required_gaps": [], "root": root.as_posix()}
            if openspec_mode == "shape"
            else pytest.fail("land readiness requested a non-shape OpenSpec audit")
        ),
    )
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda *_: {
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
    payload = _land(root)
    assert (payload["verdict"], payload["state"]) == ("block", "blocked")
    assert "openspec_completed_change_unarchived:sample-change" in payload["required_gaps"]
    assert payload["data"]["openspec_lifecycle"]["completed_changes"] == ["sample-change"]


def _assert_active_change_is_blocked(claim: str, fixture) -> None:
    head = git(fixture.worktree, "rev-parse", "HEAD")
    seed_executed_proof(fixture.worktree, head)
    candidate_head = git(fixture.candidate, "rev-parse", "HEAD")
    payload = _land(
        fixture.worktree,
        head if claim == LAND_CASES[5] else None,
        blocked=claim == LAND_CASES[5],
    )
    gaps = ["openspec_active_change_unarchived:fixture-change:work_lane"]
    assert (payload["verdict"], payload["state"], payload["required_gaps"]) == (
        "block",
        "blocked",
        gaps,
    )
    next_action = (
        f"ethos lane archive-change --change fixture-change --expect-head {head} --apply --json"
    )
    assert payload["next_action"] == next_action
    if claim == LAND_CASES[5]:
        assert payload["data"]["candidate_update"] == {}
        assert git(fixture.candidate, "rev-parse", "HEAD") == candidate_head
        return
    mutation = payload["data"]["mutation"]
    state = mutation["decision"]["subject"]["expected_state"]
    assert mutation["request"] == {
        "command": "land",
        "apply": False,
        "confirmation_present": False,
        "expect_head": None,
    }
    assert (mutation["decision"]["verdict"], mutation["decision"]["subject"]["action"]) == (
        "block",
        "candidate.integrate",
    )
    assert (
        state["source_head"],
        state["source_ref"],
        state["target_ref"],
        state["holder_ref"],
    ) == (
        head,
        "refs/heads/work/feature",
        "refs/heads/candidate/dev",
        "agent:test:case:agent-test",
    )
    assert state["lease_id"].startswith("lease:")
    assert state["lease_epoch"] == 1
    assert mutation["decision"]["required_gaps"] == gaps
    assert mutation["decision"]["mints_authority"] is False
    assert "authorized" not in mutation
    assert "proof_readiness" not in payload["data"]


def _assert_archived_land_readiness(
    claim: str, fixture, head: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    if claim == LAND_CASES[2]:
        candidate_head = git(fixture.candidate, "rev-parse", "HEAD")
        payload = _land(fixture.worktree)
        next_action = "ethos lane refresh-base --apply --authorize --expect-head <head> --json"
        expected = {
            "verdict": "block",
            "state": "blocked",
            "branch": "candidate/dev",
            "head": head,
            "candidate_head": candidate_head,
            "path": fixture.candidate.as_posix(),
            "required_gaps": ["candidate_base_stale"],
            "remediation": [
                {"gap": "candidate_base_stale", "kind": "stale_base", "next_action": next_action}
            ],
        }
        assert (payload["verdict"], payload["state"], payload["required_gaps"]) == (
            "block",
            "blocked",
            ["candidate_base_stale"],
        )
        assert payload["next_action"] == next_action.replace("<head>", head)
        assert payload["data"]["candidate_update"] == expected
        return
    if claim == LAND_CASES[3]:
        payload = _land(fixture.worktree)
        assert (payload["verdict"], payload["state"], payload["required_gaps"]) == (
            "block",
            "blocked",
            ["proof_not_proven"],
        )
        assert payload["next_action"] == f"ethos prove --execute --expect-head {head} --json"
        assert "proof_readiness" not in payload["data"]
        return
    seed_executed_proof(fixture.worktree, head, full=claim == LAND_CASES[8])
    if claim == LAND_CASES[7]:
        before = git(fixture.candidate, "rev-parse", "HEAD")
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:wrong-holder")
        payload = _land(fixture.worktree)
        assert payload["required_gaps"] == ["lease_actor_mismatch"]
        assert git(fixture.candidate, "rev-parse", "HEAD") == before
        return
    if claim == LAND_CASES[8]:
        monkeypatch.setattr(
            "ethos.domain.status.audit_for_root",
            lambda root, **_: {"verdict": "pass", "required_gaps": [], "root": root.as_posix()},
        )
    payload = _land(fixture.worktree, head)
    assert (payload["verdict"], payload["state"], payload["required_gaps"]) == (
        "pass",
        "candidate_validated",
        [],
    )
    assert git(fixture.candidate, "rev-parse", "HEAD") == head
    if claim == LAND_CASES[6]:
        proof = proof_attestation(fixture.worktree, head)
        assert proof is not None
        attestation = Attestation.model_validate(payload["data"]["candidate_update"]["attestation"])
        plan = mutable_json(attestation.payload.body["plan"])
        assert plan["prior_attestations"] == {"proof": proof.model_dump(mode="json")}


@pytest.mark.parametrize("claim", LAND_CASES, ids=LAND_CASES)
def test_land_readiness_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    if claim == LAND_CASES[0]:
        _assert_dirty_land_is_blocked(tmp_path)
        return
    if claim == LAND_CASES[1]:
        _assert_completed_change_is_blocked(monkeypatch, tmp_path)
        return
    fixture = start_adopted_work_lane(tmp_path)
    if claim == LAND_CASES[2]:
        commit_fixture_file(fixture.candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    if claim == LAND_CASES[8]:
        commit_fixture_file(
            fixture.worktree, "system/gates.toml", FULL_GATES, "declare split proof floors"
        )
        commit_fixture_file(
            fixture.worktree, ".ethos/profile.toml", FULL_PROFILE, "select split proof floors"
        )
    commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
    if claim in LAND_CASES[4:6]:
        _assert_active_change_is_blocked(claim, fixture)
        return
    head = _archive(monkeypatch, fixture.worktree)
    _assert_archived_land_readiness(claim, fixture, head, monkeypatch)


PROOF_CASES = literal_case("cli.test_contracts_land:assign:PROOF_CASES:1")


def _assert_proof_invalid_after_handoff(
    monkeypatch: pytest.MonkeyPatch, fixture, head: str, branch: str, lease: dict
) -> None:
    holder, successor = "agent:test:case:agent-test", "agent:test:case:successor"
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    assert proof_attestation(fixture.worktree, head) is not None
    assert proof_gaps(fixture.worktree, head) == []
    offer = apply_lease_operation(
        state_database(fixture.worktree),
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
        state_database(fixture.worktree),
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
    assert proof_attestation(fixture.worktree, head) is None
    assert proof_gaps(fixture.worktree, head) == ["proof_lease_generation_stale"]
    assert proof_attestation(fixture.candidate, head) is None
    assert proof_gaps(fixture.candidate, head) == ["proof_lease_generation_stale"]


def _assert_proof_requires_live_binding(
    claim: str, monkeypatch: pytest.MonkeyPatch, fixture, head: str, branch: str, lease: dict
) -> None:
    lease_state, binding = claim.removesuffix("]").split("[")[1].split("-")
    monkeypatch.setattr(
        "ethos.adapters.mutation.proof_admission.leases_by_branch",
        lambda _root: {branch: lease | {"lease_state": lease_state, "commitment_binding": binding}},
    )
    assert proof_attestation(fixture.worktree, head) is None
    assert proof_gaps(fixture.worktree, head) == ["proof_lease_generation_stale"]


@pytest.mark.parametrize("claim", PROOF_CASES, ids=PROOF_CASES)
def test_proof_authority_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture, head = _proved_lane(tmp_path, monkeypatch)
    branch = git(fixture.worktree, "branch", "--show-current")
    lease = leases_by_branch(fixture.worktree)[branch]
    if claim == PROOF_CASES[0]:
        _assert_proof_invalid_after_handoff(monkeypatch, fixture, head, branch, lease)
        return
    if claim in PROOF_CASES[1:]:
        _assert_proof_requires_live_binding(claim, monkeypatch, fixture, head, branch, lease)


REFRESH_CASES = literal_case("cli.test_contracts_land:assign:REFRESH_CASES:2")


@pytest.mark.parametrize("claim", REFRESH_CASES, ids=REFRESH_CASES)
def test_refresh_base_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    if claim == REFRESH_CASES[0]:
        commit_fixture_file(fixture.candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
        commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
        previous = git(fixture.worktree, "rev-parse", "HEAD")
        candidate = git(fixture.candidate, "rev-parse", "HEAD")
        git(fixture.worktree, "config", "commit.gpgsign", "true")
        git(fixture.worktree, "config", "user.signingkey", "missing-test-signing-key")
        payload = run_ethos(
            "lane",
            "refresh-base",
            "--apply",
            "--authorize",
            "--expect-head",
            previous,
            "--json",
            cwd=fixture.worktree,
        )
        head = git(fixture.worktree, "rev-parse", "HEAD")
        assert (
            payload["verdict"],
            payload["state"],
            payload["required_gaps"],
            payload["next_action"],
        ) == ("pass", "base_refreshed", [], "ethos land --json")
        data = payload["data"]
        assert (data["branch"], data["previous_head"], data["head"], data["candidate_head"]) == (
            "work/feature",
            previous,
            head,
            candidate,
        )
        assert head != previous
        lease = leases_by_branch(fixture.worktree)["work/feature"]
        assert lease["expected_head"] == head
        prewrite = run_ethos(
            "lane",
            "prewrite",
            "FEATURE.md",
            "--editor-root",
            fixture.worktree.as_posix(),
            "--require-editor-root",
            "--json",
            cwd=fixture.worktree,
        )
        assert (prewrite["verdict"], prewrite["state"], prewrite["required_gaps"]) == (
            "pass",
            "admitted",
            [],
        )
        assert (
            data["rebase_attestation"]["predicate"],
            data["attachment_attestation"]["predicate"],
        ) == ("effect:git-rebase", "effect:git-worktree")
        return
    commit_fixture_file(fixture.candidate, "CONFLICT.txt", "candidate\n", "advance candidate")
    previous = commit_fixture_file(fixture.worktree, "CONFLICT.txt", "work lane\n", "conflict")
    completed = run_ethos_raw(
        "lane",
        "refresh-base",
        "--apply",
        "--authorize",
        "--expect-head",
        previous,
        "--json",
        cwd=fixture.worktree,
    )
    payload = json.loads(completed.stdout)
    assert completed.returncode == 1, completed.stderr
    assert (payload["verdict"], payload["state"]) == ("block", "blocked")
    assert "ok" not in payload
    assert "refresh_base_failed" in payload["required_gaps"]
    assert git(fixture.worktree, "branch", "--show-current") == "work/feature"


BOUNDARY_CASES = literal_case("cli.test_contracts_land:assign:BOUNDARY_CASES:3")


@pytest.mark.parametrize("claim", BOUNDARY_CASES, ids=BOUNDARY_CASES)
def test_apply_boundary_claim_matrix(claim: str, tmp_path: Path) -> None:
    if claim == BOUNDARY_CASES[1]:
        with pytest.raises(AssertionError, match="--apply calls must pass cwd"):
            run_ethos_blocked("land", "--apply", "--json")
        return
    repo = init_git_repo(tmp_path / "repo")
    if claim == BOUNDARY_CASES[0]:
        payload = run_ethos_blocked("land", "--apply", "--json", cwd=repo)
        gaps = payload["required_gaps"]
        mutation = payload["data"]["mutation"]
        assert (payload["verdict"], payload["state"]) == ("block", "blocked")
        assert {
            "authorization_required",
            "expect_head_required",
        } <= set(gaps)
        assert mutation["request"]["confirmation_present"] is False
        assert mutation["decision"]["verdict"] == "block"
        assert mutation["decision"]["required_gaps"] == gaps
        assert "decision" not in {
            key: value for key, value in mutation.items() if isinstance(value, str)
        }
        return
    command = claim.removesuffix("]").split("[")[1]
    head = git(repo, "rev-parse", "HEAD")
    payload = run_ethos_blocked(
        command, "--apply", "--authorize", "--expect-head", head, "--json", cwd=repo
    )
    assert (payload["verdict"], payload["state"]) == (
        "block",
        "blocked",
    )
    assert "protected_root_mutation" in payload["required_gaps"]


CLOSEOUT_CASES = literal_case("cli.test_contracts_land:assign:CLOSEOUT_CASES:4")


def _assert_first_commitment_can_close(repo: Path, candidate: Path) -> None:
    commitment = repo / ".ethos/commitment.toml"
    text = commitment.read_text()
    git(repo, "rm", ".ethos/commitment.toml")
    _commit(repo, "represent the pre-commitment accepted root")
    accepted = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted)
    (candidate / ".ethos/commitment.toml").write_text(text)
    git(candidate, "add", ".ethos/commitment.toml")
    _commit(candidate, "introduce the first repository commitment")
    head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, head)
    report = accepted_mutation.promote_candidate(
        root=repo,
        policy=load_branch_role_policy(repo),
        current_head=accepted,
        candidate_head=head,
        status=workspace_status(repo),
    )
    assert (
        report["verdict"],
        report["previous_head"],
        report["head"],
        git(repo, "rev-parse", "dev"),
    ) == ("pass", accepted, head, head)
    assert (
        report["attestation"]["commitment_digest"]
        == load_repository_commitment(repo, tree_ref=head).digest()
    )


def _assert_first_cas_uses_accepted_policy(repo: Path, candidate: Path) -> None:
    accepted = git(repo, "rev-parse", "HEAD")
    target = candidate / ".ethos/workspace.toml"
    target.write_text(CHANGED_TOPOLOGY)
    git(candidate, "add", target.as_posix())
    _commit(candidate, "change future branch topology")
    head = git(candidate, "rev-parse", "HEAD")
    git(repo, "branch", "candidate-selected-accepted", accepted)
    seed_executed_proof(candidate, head)
    report = landing_mutation.apply_candidate_to_accepted(
        root=repo, authorized=True, expect_head=accepted
    )
    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == head
    assert git(repo, "rev-parse", "candidate-selected-accepted") == accepted


def _assert_declared_closeout_policy(claim: str, repo: Path, candidate: Path) -> None:
    workspace = repo / ".ethos/workspace.toml"
    if claim == CLOSEOUT_CASES[2]:
        git(repo, "rm", ".ethos/workspace.toml")
        _commit(repo, "use default branch roles")
        accepted = git(repo, "rev-parse", "HEAD")
        git(candidate, "reset", "--hard", accepted)
        assert (repo / ".ethos/profile.toml").is_file()
        assert not workspace.exists()
    elif claim == CLOSEOUT_CASES[3]:
        workspace.write_text('[branch_roles]\naccepted_branch = "dev"\n')
        git(repo, "add", workspace.as_posix())
        _commit(repo, "record incomplete branch roles")
        accepted = git(repo, "rev-parse", "HEAD")
        git(candidate, "reset", "--hard", accepted)
        report = landing_mutation.apply_candidate_to_accepted(
            root=repo, authorized=True, expect_head=accepted
        )
        assert report["verdict"] == "block"
        assert report["required_gaps"] == ["accepted_policy_unavailable"]
        return
    else:
        workspace.write_text(
            workspace.read_text().replace(
                'release_mirror = "independent"', 'release_mirror = "accepted_ff"'
            )
        )
        git(repo, "add", workspace.as_posix())
        _commit(repo, "require release mirror")
        accepted = git(repo, "rev-parse", "HEAD")
        git(repo, "branch", "main", accepted)
        git(candidate, "reset", "--hard", accepted)
        workspace.write_text(
            workspace.read_text().replace(
                'release_mirror = "accepted_ff"', 'release_mirror = "independent"'
            )
        )
        git(repo, "update-index", "--skip-worktree", ".ethos/workspace.toml")
    head = commit_fixture_file(candidate, "README.md", "# candidate\n", "candidate")
    seed_executed_proof(candidate, head)
    report = landing_mutation.apply_candidate_to_accepted(
        root=repo, authorized=True, expect_head=accepted
    )
    assert report["verdict"] == "pass"
    assert git(repo, "rev-parse", "dev") == head
    if claim == CLOSEOUT_CASES[4]:
        assert git(repo, "rev-parse", "main") == head


@pytest.mark.parametrize("claim", CLOSEOUT_CASES, ids=CLOSEOUT_CASES)
def test_closeout_policy_claim_matrix(claim: str, tmp_path: Path) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    if claim == CLOSEOUT_CASES[0]:
        _assert_first_commitment_can_close(repo, candidate)
        return
    if claim == CLOSEOUT_CASES[1]:
        _assert_first_cas_uses_accepted_policy(repo, candidate)
        return
    _assert_declared_closeout_policy(claim, repo, candidate)


CAS_CASES = literal_case("cli.test_contracts_land:assign:CAS_CASES:5")


@pytest.mark.parametrize("claim", CAS_CASES, ids=CAS_CASES)
def test_candidate_cas_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture, head = _proved_lane(tmp_path, monkeypatch)
    original = landing_mutation.execute_candidate_plan
    attempts = 0
    plans: list[int] = []
    if claim == CAS_CASES[1]:
        git(fixture.candidate, "reset", "--hard", head)

        def effect(*_args, **_kwargs):
            msg = "equal candidate must not compile a Git mutation"
            raise AssertionError(msg)
    else:

        def effect(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            plans.append(id(args[1]))
            if claim == CAS_CASES[3] and attempts == 1:
                commit_fixture_file(fixture.candidate, "PEER.md", "# peer\n", "peer progress")
            if claim != CAS_CASES[0] or attempts == 1:
                msg = "git_effect_cas_rejected"
                raise ValueError(msg)
            return original(*args, **kwargs)

    monkeypatch.setattr(landing_mutation, "execute_candidate_plan", effect)
    payload = _land(fixture.worktree, head, blocked=claim in CAS_CASES[2:])
    update = payload["data"]["candidate_update"]
    if claim == CAS_CASES[0]:
        assert attempts == 2
        assert len(set(plans)) == 1
        assert payload["verdict"] == "pass"
        assert update["cas_attempts"] == 2
        assert git(fixture.candidate, "rev-parse", "HEAD") == head
    elif claim == CAS_CASES[1]:
        assert (
            payload["verdict"],
            payload["state"],
            update["attestation"],
            update["cas_attempts"],
        ) == ("pass", "candidate_current", {}, 0)
        assert git(fixture.candidate, "rev-parse", "HEAD") == head
    elif claim == CAS_CASES[2]:
        assert attempts == 2
        assert payload["required_gaps"] == ["candidate_cas_retry_exhausted"]
        assert update["cas_attempts"] == 2
    else:
        candidate = git(fixture.candidate, "rev-parse", "HEAD")
        assert attempts == 1
        assert payload["required_gaps"] == ["candidate_cas_stale"]
        assert update["candidate_head"] == candidate
        assert update["cas_attempts"] == 1
        assert candidate != head
