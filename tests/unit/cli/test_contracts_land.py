from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.landing as landing_mutation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import apply_lease_operation
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import lane_start_arguments
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.literal_cases import literal_case
from tests.support.openspec_lifecycle import stub_official_archive_state

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures/contracts-land"
FULL_GATES = (FIXTURE_ROOT / "full-gates.toml").read_text()
FULL_PROFILE = (FIXTURE_ROOT / "full-profile.toml").read_text()
CHANGED_TOPOLOGY = (FIXTURE_ROOT / "changed-topology.toml").read_text()


def _archive(monkeypatch: pytest.MonkeyPatch, root: Path, *, full: bool = False) -> str:
    head = commit_fixture_file(
        root,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "complete fixture change",
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(root, head, full=full)
    archived = run_ethos(
        "lane",
        "archive-change",
        "--change",
        "fixture-change",
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=root,
    )
    assert archived["verdict"] == "pass", archived
    return git(root, "rev-parse", "HEAD")


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


def _proved_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, full: bool = False):
    fixture = start_adopted_work_lane(tmp_path)
    commit_fixture_file(fixture.worktree, "FEATURE.md", "# feature\n", "feature work")
    head = _archive(monkeypatch, fixture.worktree, full=full)
    seed_executed_proof(fixture.worktree, head, full=full)
    return fixture, head


LAND_CASES = literal_case("cli.test_contracts_land:assign:LAND_CASES:0")


def _assert_dirty_land_is_blocked(tmp_path: Path) -> None:
    repo, _ = start_adopted_candidate(tmp_path)
    root = tmp_path / "repo-work-feature"
    run_ethos(*lane_start_arguments(repo, root), cwd=repo)
    (root / "README.md").write_text("# dirty\n")
    payload = _land(root)
    assert (payload["verdict"], payload["state"]) == ("block", "blocked")
    assert "work_lane_dirty" in payload["required_gaps"]


def _assert_completed_change_is_blocked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo, _ = start_adopted_candidate(tmp_path)
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
    stub_official_archive_state(monkeypatch, completed=True, change_name="sample-change")
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
    assert state["lease_generation"] == 1
    assert state["lease_expires_at"]
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
    head = _archive(monkeypatch, fixture.worktree, full=claim == LAND_CASES[8])
    _assert_archived_land_readiness(claim, fixture, head, monkeypatch)


def test_work_lane_proof_is_invalid_after_same_head_lease_transfer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture, head = _proved_lane(tmp_path, monkeypatch)
    branch = git(fixture.worktree, "branch", "--show-current")
    lease = leases_by_branch(fixture.worktree)[branch]
    holder, successor = "agent:test:case:agent-test", "agent:test:case:successor"
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    assert proof_attestation(fixture.worktree, head) is not None
    assert proof_gaps(fixture.worktree, head) == []
    transferred = apply_lease_operation(
        state_database(fixture.worktree),
        request=LeaseOperationRequest(
            operation="transfer",
            branch=branch,
            holder_ref=holder,
            target_holder_ref=successor,
            generation=int(lease["generation"]),
            expires_at=str(lease["expires_at"]),
            apply=True,
        ),
    )
    assert (transferred["holder_ref"], transferred["generation"]) == (
        successor,
        int(lease["generation"]) + 1,
    )
    assert proof_attestation(fixture.worktree, head) is None
    assert proof_gaps(fixture.worktree, head) == ["proof_lease_generation_stale"]
    assert proof_attestation(fixture.candidate, head) is None
    assert proof_gaps(fixture.candidate, head) == ["proof_lease_generation_stale"]


@pytest.mark.parametrize("lease_state", ["expired", "unknown"])
def test_work_lane_proof_requires_a_live_lease(
    lease_state: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fixture, head = _proved_lane(tmp_path, monkeypatch)
    branch = git(fixture.worktree, "branch", "--show-current")
    lease = leases_by_branch(fixture.worktree)[branch]
    monkeypatch.setattr(
        "ethos.adapters.mutation.proof_admission.leases_by_branch",
        lambda _root: {branch: lease | {"lease_state": lease_state}},
    )
    assert proof_attestation(fixture.worktree, head) is None
    assert proof_gaps(fixture.worktree, head) == ["proof_lease_generation_stale"]


REFRESH_CASES = literal_case("cli.test_contracts_land:assign:REFRESH_CASES:2")


@pytest.mark.parametrize("claim", REFRESH_CASES, ids=REFRESH_CASES)
def test_refresh_base_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture = start_adopted_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    if claim == REFRESH_CASES[0]:
        generation = leases_by_branch(fixture.worktree)["work/feature"]["generation"]
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
        ) == (
            "pass",
            "base_refreshed",
            [],
            f"ethos land --root {fixture.worktree.resolve().as_posix()} --json",
        )
        data = payload["data"]
        assert (data["branch"], data["previous_head"], data["head"], data["candidate_head"]) == (
            "work/feature",
            previous,
            head,
            candidate,
        )
        assert head != previous
        lease = leases_by_branch(fixture.worktree)["work/feature"]
        assert lease["generation"] == generation
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


def _assert_first_cas_uses_accepted_policy(fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, candidate, worktree = fixture
    accepted = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate-selected-accepted", accepted)
    target = worktree / ".ethos/workspace.toml"
    target.write_text(CHANGED_TOPOLOGY)
    git(worktree, "add", target.as_posix())
    _commit(worktree, "change future branch topology")
    head = _archive(monkeypatch, worktree)
    seed_executed_proof(worktree, head)
    landed = _land(worktree, head)
    assert landed["verdict"] == "pass", landed
    assert git(candidate, "rev-parse", "HEAD") == head
    report = landing_mutation.apply_candidate_to_accepted(
        root=repo, authorized=True, expect_head=accepted
    )
    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == head
    assert git(repo, "rev-parse", "candidate-selected-accepted") == accepted


def _assert_declared_closeout_policy(
    claim: str,
    repo: Path,
    candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = repo / ".ethos/workspace.toml"
    if claim == CLOSEOUT_CASES[1]:
        git(repo, "rm", ".ethos/workspace.toml")
        _commit(repo, "use default branch roles")
        accepted = git(repo, "rev-parse", "HEAD")
        git(candidate, "reset", "--hard", accepted)
        assert (repo / ".ethos/profile.toml").is_file()
        assert not workspace.exists()
    elif claim == CLOSEOUT_CASES[2]:
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
    worktree = create_change_source_lane(
        repo,
        repo.parent / "repo-work-closeout",
        branch="work/closeout",
        holder_ref="agent:test:case:agent-test",
    )
    commit_fixture_file(worktree, "README.md", "# candidate\n", "candidate")
    head = _archive(monkeypatch, worktree)
    seed_executed_proof(worktree, head)
    landed = _land(worktree, head)
    assert landed["verdict"] == "pass", landed
    assert git(candidate, "rev-parse", "HEAD") == head
    report = landing_mutation.apply_candidate_to_accepted(
        root=repo, authorized=True, expect_head=accepted
    )
    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == head
    if claim == CLOSEOUT_CASES[3]:
        assert git(repo, "rev-parse", "main") == head


@pytest.mark.parametrize("claim", CLOSEOUT_CASES, ids=CLOSEOUT_CASES)
def test_closeout_policy_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    if claim == CLOSEOUT_CASES[0]:
        _assert_first_cas_uses_accepted_policy(start_adopted_work_lane(tmp_path), monkeypatch)
        return
    repo, candidate = start_adopted_candidate(tmp_path)
    _assert_declared_closeout_policy(claim, repo, candidate, monkeypatch)


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
