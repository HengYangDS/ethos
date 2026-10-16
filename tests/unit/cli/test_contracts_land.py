"""Public source integration, proof and exact-authority acceptance cases."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.accepted.admission as accepted_admission
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
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_release_mirror
from tests.support.literal_cases import literal_case
from tests.support.proof import seed_executed_proof

FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures/contracts-land"
FULL_GATES = (FIXTURE_ROOT / "full-gates.toml").read_text()
CHANGED_TOPOLOGY = (FIXTURE_ROOT / "changed-topology.toml").read_text()


def _archive(monkeypatch: pytest.MonkeyPatch, root: Path, *, full: bool = False) -> str:
    head = commit_fixture_file(
        root,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "test: complete fixture change",
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(root, head, full=full)
    archived = run_ethos_blocked(
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
    assert archived["required_gaps"] == ["proof_not_proven"], archived
    return git(root, "rev-parse", "HEAD")


def _land(root: Path, head: str | None = None, *, blocked: bool = False) -> dict[str, object]:
    args = ["land"]
    if head is not None:
        args += ["--apply", "--authorize", "--expect-head", head]
    args += ["--json"]
    return (run_ethos_blocked if blocked else run_ethos)(*args, cwd=root)


def _proved_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, full: bool = False):
    fixture = prepared_work_lane(tmp_path)
    commit_fixture_file(fixture.worktree, "notes/feature.md", "# feature\n", "test: feature work")
    head = _archive(monkeypatch, fixture.worktree, full=full)
    seed_executed_proof(fixture.worktree, head, full=full)
    return fixture, head


LAND_CASES = literal_case("cli.test_contracts_land:assign:LAND_CASES:0")


def _assert_dirty_land_is_blocked(tmp_path: Path) -> None:
    repo, _ = start_adopted_candidate(tmp_path)
    root = Path(run_ethos(*lane_start_arguments(repo), cwd=repo)["data"]["path"])
    (root / "README.md").write_text("# dirty\n")
    payload = _land(root)
    assert (payload["verdict"], payload["state"]) == ("block", "blocked")
    assert "work_lane_dirty" in payload["required_gaps"]


def _assert_completed_change_is_observed(tmp_path: Path) -> None:
    fixture = prepared_work_lane(tmp_path)
    commit_fixture_file(
        fixture.worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "test: complete source work",
    )
    payload = _land(fixture.worktree)
    assert (payload["verdict"], payload["state"]) == ("block", "blocked")
    assert payload["required_gaps"] == ["proof_not_proven"]
    assert payload["data"]["openspec_lifecycle"]["completed_changes"] == ["fixture-change"]


def _assert_active_change_is_admitted(claim: str, fixture) -> None:
    """Exact source integration preserves unfinished official progress."""
    head = git(fixture.worktree, "rev-parse", "HEAD")
    seed_executed_proof(fixture.worktree, head)
    candidate_head = git(fixture.candidate, "rev-parse", "HEAD")
    pending = (fixture.worktree / "openspec/changes/fixture-change/tasks.md").read_bytes()
    applied = claim == LAND_CASES[5]
    payload = _land(fixture.worktree, head if applied else None)
    assert payload["verdict"] == "pass"
    assert payload["required_gaps"] == []
    assert (fixture.worktree / "openspec/changes/fixture-change/tasks.md").read_bytes() == pending
    assert git(fixture.candidate, "rev-parse", "HEAD") == (head if applied else candidate_head)
    if not applied:
        decision = payload["data"]["mutation"]["decision"]
        assert decision["subject"]["action"] == "candidate.integrate"
        assert decision["mints_authority"] is False


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
        assert payload["next_action"] == f"ethos prove --full --execute --expect-head {head} --json"
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
        _assert_completed_change_is_observed(tmp_path)
        return
    fixture = prepared_work_lane(tmp_path)
    if claim == LAND_CASES[2]:
        commit_fixture_file(
            fixture.candidate, "CANDIDATE.md", "# candidate\n", "test: advance candidate"
        )
    if claim == LAND_CASES[8]:
        commit_fixture_file(
            fixture.worktree, "system/gates.toml", FULL_GATES, "test: declare split proof floors"
        )
    commit_fixture_file(fixture.worktree, "notes/feature.md", "# feature\n", "test: feature work")
    if claim in LAND_CASES[4:6]:
        _assert_active_change_is_admitted(claim, fixture)
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
    fixture = prepared_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    if claim == REFRESH_CASES[0]:
        generation = leases_by_branch(fixture.worktree)["work/feature"]["generation"]
        commit_fixture_file(
            fixture.candidate, "CANDIDATE.md", "# candidate\n", "test: advance candidate"
        )
        commit_fixture_file(
            fixture.worktree, "notes/feature.md", "# feature\n", "test: feature work"
        )
        previous = git(fixture.worktree, "rev-parse", "HEAD")
        candidate = git(fixture.candidate, "rev-parse", "HEAD")
        refresh = ("lane", "refresh-base", "--apply", "--authorize", "--expect-head", previous)
        signer = git(fixture.worktree, "config", "--local", "user.signingkey")
        git(fixture.worktree, "config", "user.signingkey", "missing-test-signing-key")
        unsigned = run_ethos_blocked(*refresh, "--json", cwd=fixture.worktree)
        assert (unsigned["verdict"], unsigned["required_gaps"]) == (
            "block",
            ["git_effect_signing_key_invalid"],
        )
        assert git(fixture.worktree, "rev-parse", "HEAD") == previous
        git(fixture.worktree, "config", "user.signingkey", signer)
        payload = run_ethos(*refresh, "--json", cwd=fixture.worktree)
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
            "notes/feature.md",
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
    commit_fixture_file(fixture.candidate, "CONFLICT.txt", "candidate\n", "test: advance candidate")
    previous = commit_fixture_file(
        fixture.worktree, "CONFLICT.txt", "work lane\n", "test: conflict"
    )
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
    release = git(repo, "branch", "--list", "main")
    target = worktree / ".ethos/release.toml"
    target.write_text(f"{target.read_text()}\n{CHANGED_TOPOLOGY}")
    git(worktree, "add", target.as_posix())
    git(worktree, "commit", "-m", "test: change future branch topology")
    head = _archive(monkeypatch, worktree)
    seed_executed_proof(worktree, head)
    landed = _land(worktree, head)
    assert landed["verdict"] == "pass", landed
    assert git(candidate, "rev-parse", "HEAD") == head
    report = accepted_admission.candidate_to_accepted(
        root=repo, authorized=True, expect_head=accepted
    )
    assert report["verdict"] == "pass", report
    assert git(repo, "rev-parse", "dev") == head
    # The accepted policy mirrors main independently, so the candidate's accepted_ff
    # mirror does not move main in the closeout that first accepts it.
    assert git(repo, "branch", "--list", "main") == release


def _assert_declared_closeout_policy(
    claim: str,
    repo: Path,
    candidate: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = repo / ".ethos/release.toml"
    if claim == CLOSEOUT_CASES[1]:
        accepted = git(repo, "rev-parse", "HEAD")
        assert (repo / ".ethos/profile.toml").is_file()
        assert not (repo / ".ethos/workspace.toml").exists()
        assert "[release]" not in release.read_text()
    elif claim == CLOSEOUT_CASES[2]:
        release.write_text(f'{release.read_text()}\n[release]\nmirror = "mirror"\n')
        git(repo, "add", release.as_posix())
        git(repo, "commit", "-m", "test: record an invalid release mirror")
        accepted = git(repo, "rev-parse", "HEAD")
        git(candidate, "reset", "--hard", accepted)
        report = accepted_admission.candidate_to_accepted(
            root=repo, authorized=True, expect_head=accepted
        )
        assert report["verdict"] == "block"
        assert report["required_gaps"] == ["accepted_policy_unavailable"]
        return
    else:
        write_release_mirror(repo, "accepted_ff")
        git(repo, "add", release.as_posix())
        git(repo, "commit", "-m", "test: require release mirror")
        accepted = git(repo, "rev-parse", "HEAD")
        git(repo, "branch", "main", accepted)
        git(candidate, "reset", "--hard", accepted)
        write_release_mirror(repo, "independent")
        git(repo, "update-index", "--skip-worktree", ".ethos/release.toml")
    worktree = create_change_source_lane(
        repo,
        repo.parent / "repo-work-closeout",
        branch="work/closeout",
        holder_ref="agent:test:case:agent-test",
    )
    commit_fixture_file(worktree, "README.md", "# candidate\n", "test: candidate")
    head = _archive(monkeypatch, worktree)
    seed_executed_proof(worktree, head)
    landed = _land(worktree, head)
    assert landed["verdict"] == "pass", landed
    assert git(candidate, "rev-parse", "HEAD") == head
    report = accepted_admission.candidate_to_accepted(
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
        _assert_first_cas_uses_accepted_policy(prepared_work_lane(tmp_path), monkeypatch)
        return
    repo, candidate = start_adopted_candidate(tmp_path)
    _assert_declared_closeout_policy(claim, repo, candidate, monkeypatch)


CAS_CASES = literal_case("cli.test_contracts_land:assign:CAS_CASES:5")


@pytest.mark.parametrize("claim", CAS_CASES, ids=CAS_CASES)
def test_candidate_cas_claim_matrix(
    claim: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fixture, head = _proved_lane(tmp_path, monkeypatch)
    original = landing_mutation.execute_git_effect
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
                commit_fixture_file(fixture.candidate, "PEER.md", "# peer\n", "test: peer progress")
            if claim != CAS_CASES[0] or attempts == 1:
                msg = "git_effect_cas_rejected"
                raise ValueError(msg)
            return original(*args, **kwargs)

    monkeypatch.setattr(landing_mutation, "execute_git_effect", effect)
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
