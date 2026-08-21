from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.mutation.lane_start_carrier as lane_start_carrier
import ethos.adapters.mutation.lanes as lanes
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.openspec.profile import load_profile_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.coordination import FOREIGN_WORK_LANE_NEXT_ACTION
from ethos.adapters.repo.coordination import ForeignLaneContext
from ethos.adapters.repo.coordination import foreign_work_lane
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.adapters.repo.status.bindings import closeout_support
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.coordination import LaneLease
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.lifecycle_cases import LaneStartCase
from tests.support.literal_cases import literal_case
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path

_HOLDER = "agent:test:case:agent-test"
_LEASE_COORDINATES = literal_case("lanes.test_lane_family_profile:assign:_LEASE_COORDINATES:0")


@pytest.fixture
def lane_case(tmp_path: Path) -> LaneStartCase:
    return LaneStartCase.create(tmp_path, holder=_HOLDER)


def _assert_absent(case: LaneStartCase, report: dict[str, object], gap: str) -> None:
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]
    case.assert_absent()


def test_work_lane_projections_preserve_exact_carrier_coordinates() -> None:
    lease = {
        "lane_incarnation_id": "lane-incarnation:example",
        "lease_id": "lease:example",
        "holder_ref": _HOLDER,
        "epoch": 2,
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "issued_at": "2026-08-01T00:00:00+00:00",
        "renewed_at": "2026-08-01T00:00:00+00:00",
        "path_scope": ["src/**"],
        "base_commitment_path": "openspec/changes/example/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
        "expires_at": "2026-08-02T00:00:00+00:00",
        "payload_sha256": "e" * 64,
        "lease_state": "valid",
        "commitment_binding": "mismatch",
    }
    summary = lease_generation(lease)
    support = closeout_support(
        branch="work/example",
        role=ROLE_WORK_LANE,
        dirty=False,
        candidate={
            "exists": False,
            "worktree_exists": False,
            "branch": "candidate/dev",
            "worktree_path": "",
        },
        lease_by_branch={"work/example": lease},
        coordination_required_gaps=[],
    )
    summary_names = (
        "expected_head",
        "expected_tree",
        "issued_at",
        "renewed_at",
        "path_scope",
        "base_commitment_path",
        "base_commitment_bytes_sha256",
        "base_commitment_digest",
    )
    support_names = summary_names[:2] + summary_names[5:7]
    assert {name: lease[name] for name in summary_names}.items() <= summary.items()
    assert {f"lease_{name}": lease[name] for name in support_names}.items() <= support.items()
    assert support["base_commitment_digest"] == lease["base_commitment_digest"]


@pytest.mark.parametrize(
    ("workspace", "path", "gap"),
    [
        pytest.param(
            "[branch_roles]\ncanonical_sibling_worktrees = true\n",
            "outside",
            "work_lane_path_not_canonical",
            id="canonical_sibling_profile_rejects_noncanonical_path",
        ),
        pytest.param(
            '[branch_roles]\ncanonical_sibling_worktrees = true\nwork_branch_prefix = "lane/"\n',
            None,
            "repository_family_profile_requires_work_branch_prefix",
            id="canonical_sibling_profile_requires_configured_work_branch_prefix",
        ),
    ],
)
def test_profile_admission_claims(
    tmp_path: Path,
    workspace: str,
    path: str | None,
    gap: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos/workspace.toml").write_text(workspace, encoding="utf-8")
    report = start_work_lane(
        root=repo,
        name="feature",
        source_root=repo,
        path=tmp_path / path if path else None,
        holder_ref=_HOLDER,
    )
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]


def test_canonical_sibling_profile_uses_date_bound_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".ethos/workspace.toml").write_text(
        "[branch_roles]\ncanonical_sibling_worktrees = true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lanes, "utc_now", lambda: datetime(2026, 7, 22, tzinfo=UTC))
    report = start_work_lane(
        root=repo,
        name="retired lane admission",
        source_root=repo,
        holder_ref=_HOLDER,
    )
    lane_id = "20260722-retired-lane-admission"
    assert report["branch"] == f"work/{lane_id}"
    assert report["path"] == (tmp_path / "repo-worktrees" / lane_id).as_posix()


def test_start_work_lane_returns_the_bound_actor_lease_and_carrier_receipt(
    lane_case: LaneStartCase,
) -> None:
    report = lane_case.start(holder=_HOLDER)
    leases = leases_by_branch(lane_case.repo)
    lease = report["lease"]
    assert isinstance(lease, dict)
    assert {
        "verdict": "pass",
        "state": "started",
        "branch": "work/feature",
        "base": "candidate/dev",
        "base_head": git(lane_case.candidate, "rev-parse", "HEAD"),
        "path": lane_case.target.resolve().as_posix(),
        "holder_ref": _HOLDER,
        "required_gaps": [],
    }.items() <= report.items()
    assert hook_runtime_binding(lane_case.target).items() <= report["hook_runtime"].items()
    assert report["hook_runtime"]["legacy_runtime_locator"] == {
        "path": (lane_case.repo / ".git" / "ethos-runtime-python").as_posix(),
        "state": "absent",
        "removed": False,
    }
    assert report["hook_runtime"]["required_gaps"] == []
    assert "claim_id" not in report
    assert (
        report["base_commitment_digest"]
        == load_profile_commitment(
            lane_case.source,
            tree_ref=git(lane_case.source, "rev-parse", "HEAD"),
        ).digest()
    )
    assert report["worktree"] == {
        "branch": "work/feature",
        "path": lane_case.target.resolve().as_posix(),
        "head": report["head"],
        "role": "work_lane",
        "worktree_binding": "linked",
    }
    assert lease == {
        key: value for key, value in leases["work/feature"].items() if key != "commitment_binding"
    }
    assert "work/change-source" not in leases
    assert report["source_lease_state"] == "revoked"
    assert (
        lease["base_commitment_digest"],
        lease["expected_head"],
        lease["expected_tree"],
        lease["base_commitment_path"],
    ) == (
        report["base_commitment_digest"],
        report["head"],
        git(lane_case.target, "rev-parse", "HEAD^{tree}"),
        "openspec/changes/fixture-change/commitment.toml",
    )
    assert "materialized_carrier" not in report
    assert (
        lease["base_commitment_bytes_sha256"]
        == hashlib.sha256(
            (lane_case.target / lease["base_commitment_path"]).read_bytes()
        ).hexdigest()
    )
    support = workspace_status(lane_case.target, include_foreign_path_scope=False)[
        "closeout_support"
    ]
    assert support["commitment_binding"] == "bound"
    names = (
        "expected_head",
        "expected_tree",
        "base_commitment_path",
        "base_commitment_bytes_sha256",
    )
    assert {f"lease_{name}": lease[name] for name in names}.items() <= support.items()
    assert support["base_commitment_digest"] == lease["base_commitment_digest"]


def test_start_work_lane_signs_and_verifies_materialized_carrier(
    lane_case: LaneStartCase,
    tmp_path: Path,
) -> None:
    signing_key = tmp_path / "lane-start-signing-key"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(signing_key)),
        check=True,
        capture_output=True,
        text=True,
    )
    public_key = signing_key.with_suffix(".pub")
    allowed_signers = tmp_path / "lane-start-allowed-signers"
    allowed_signers.write_text(
        f'test@example.invalid namespaces="git" {public_key.read_text(encoding="utf-8").strip()}\n',
        encoding="utf-8",
    )
    allowed_signers.chmod(0o600)
    git(lane_case.repo, "config", "commit.gpgsign", "true")
    git(lane_case.repo, "config", "gpg.format", "ssh")
    git(lane_case.repo, "config", "gpg.ssh.program", "/usr/bin/ssh-keygen")
    git(
        lane_case.repo,
        "config",
        "gpg.ssh.allowedSignersFile",
        allowed_signers.as_posix(),
    )
    git(lane_case.repo, "config", "user.signingkey", public_key.as_posix())

    report = lane_case.start(holder=_HOLDER)

    assert report["verdict"] == "pass", report["required_gaps"]
    assert git(lane_case.target, "log", "-1", "--format=%G?") == "G"


def test_start_work_lane_rejects_untrusted_materialized_carrier(
    lane_case: LaneStartCase,
    tmp_path: Path,
) -> None:
    signing_key = tmp_path / "lane-start-untrusted-key"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(signing_key)),
        check=True,
        capture_output=True,
        text=True,
    )
    empty_anchor = tmp_path / "lane-start-empty-allowed-signers"
    empty_anchor.write_text("", encoding="utf-8")
    empty_anchor.chmod(0o600)
    git(lane_case.repo, "config", "commit.gpgsign", "true")
    git(lane_case.repo, "config", "gpg.format", "ssh")
    git(lane_case.repo, "config", "gpg.ssh.program", "/usr/bin/ssh-keygen")
    git(
        lane_case.repo,
        "config",
        "gpg.ssh.allowedSignersFile",
        empty_anchor.as_posix(),
    )
    git(
        lane_case.repo,
        "config",
        "user.signingkey",
        signing_key.with_suffix(".pub").as_posix(),
    )

    report = lane_case.start(holder=_HOLDER)

    assert report["verdict"] == "block"
    assert "commit_signature_untrusted" in report["required_gaps"]
    lane_case.assert_absent()


def test_start_work_lane_rejects_foreign_source_lease_holder(
    tmp_path: Path,
) -> None:
    case = LaneStartCase.create(tmp_path, holder="agent:test:case:source")

    report = case.start(holder=_HOLDER)

    _assert_absent(case, report, "source_lease_holder_mismatch")
    assert leases_by_branch(case.repo)["work/change-source"]["lease_state"] == "valid"


def test_start_work_lane_preserves_source_when_successor_lease_conflicts(
    lane_case: LaneStartCase,
) -> None:
    before = leases_by_branch(lane_case.repo)["work/change-source"]
    conflict = LaneLease.from_payload(dict(before["payload"])).model_copy(
        update={
            "lane_incarnation_id": "lane-incarnation:conflict",
            "lease_id": "lease:conflict",
            "lane_ref": "work/feature",
        }
    )
    acquire_lease(state_database(lane_case.repo), lease=conflict)

    report = lane_case.start(holder=_HOLDER)

    leases = leases_by_branch(lane_case.repo)
    assert report["required_gaps"] == ["lane_lease_conflict:work/feature"]
    assert leases["work/change-source"] == before
    assert leases["work/feature"]["lease_id"] == "lease:conflict"
    assert ref_head(lane_case.repo, "work/feature") == ""
    assert not lane_case.target.exists()


def test_start_work_lane_restores_source_after_post_ref_failure(
    lane_case: LaneStartCase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = leases_by_branch(lane_case.repo)["work/change-source"]
    monkeypatch.setattr(
        lane_start_carrier,
        "install_hook_launchers",
        lambda _root: (_ for _ in ()).throw(ValueError("runtime invalid")),
    )

    report = lane_case.start(holder=_HOLDER)

    leases = leases_by_branch(lane_case.repo)
    assert report["required_gaps"] == ["lane_start_hook_runtime_binding_failed"]
    assert report["source_lease_state"] == "restored"
    assert leases["work/change-source"] == before
    assert "work/feature" not in leases
    assert ref_head(lane_case.repo, "work/feature") == ""
    assert not lane_case.target.exists()


@pytest.mark.parametrize(
    ("gaps", "lease_state", "foreign_ref"),
    [
        pytest.param(
            ["lane_start_ref_creation_failed"],
            "revoked",
            False,
            id="start_work_lane_revokes_final_lease_when_ref_creation_fails",
        ),
        pytest.param(
            ["lane_creation_compensation_failed", "lane_start_ref_changed"],
            "revoked",
            True,
            id="start_work_lane_preserves_foreign_ref_and_restores_source_lease",
        ),
    ],
)
def test_start_work_lane_ref_creation_transaction_claims(
    lane_case: LaneStartCase,
    monkeypatch: pytest.MonkeyPatch,
    gaps: list[str],
    lease_state: str,
    *,
    foreign_ref: bool,
) -> None:
    source_lease = leases_by_branch(lane_case.repo)["work/change-source"]
    foreign_head = git(lane_case.candidate, "rev-parse", "HEAD")

    def fail_ref_creation(*_args: object, **_kwargs: object) -> None:
        if foreign_ref:
            git(lane_case.repo, "update-ref", "refs/heads/work/feature", foreign_head)
        message = "injected ref failure"
        raise ValueError(message)

    monkeypatch.setattr(lane_start_carrier, "execute_git_effect", fail_ref_creation)
    report = lane_case.start(holder=_HOLDER)
    assert report["lease_state"] == lease_state
    assert report["required_gaps"] == gaps
    leases = leases_by_branch(lane_case.repo)
    if foreign_ref:
        assert ref_head(lane_case.repo, "work/feature") == foreign_head
        assert "work/feature" not in leases
        assert leases["work/change-source"] == source_lease
        assert report["source_lease_state"] == "restored"
    else:
        lane_case.assert_absent()
        assert leases["work/change-source"]["lease_state"] == "valid"
        assert report["source_lease_state"] == "restored"
    assert not lane_case.target.exists()


@pytest.mark.parametrize(
    "claim",
    literal_case(
        "lanes.test_lane_family_profile:parametrize:test_start_work_lane_lease_precedes_ref_creation:1"
    ),
)
def test_start_work_lane_lease_precedes_ref_creation(
    lane_case: LaneStartCase,
    monkeypatch: pytest.MonkeyPatch,
    claim: str,
) -> None:
    observed: list[str] = []
    replace_lease_authority = lanes.replace_lease_authority

    def observe_lease(*args: object, **kwargs: object):
        observed.append(kwargs["lease"].expected_head)
        assert ref_head(lane_case.repo, "work/feature") == ""
        return replace_lease_authority(*args, **kwargs)

    monkeypatch.setattr(lanes, "replace_lease_authority", observe_lease)
    base_head = git(lane_case.candidate, "rev-parse", "HEAD")
    report = lane_case.start(holder=_HOLDER)
    assert report["verdict"] == "pass"
    assert report["head"] != base_head
    assert observed == [report["head"]]
    assert ref_head(lane_case.repo, "work/feature") == report["head"]
    assert claim


def test_foreign_and_unbound_lane_observation_only_requests_handoff_or_takeover(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    foreign = create_change_source_lane(
        repo,
        tmp_path / "repo-work-foreign",
        branch="work/foreign",
        holder_ref="agent:test:case:foreign",
    )
    lease = leases_by_branch(repo)["work/foreign"]
    lane = foreign_work_lane(
        {
            "path": foreign.as_posix(),
            "head": git(foreign, "rev-parse", "HEAD"),
            "branch": "work/foreign",
            "role": "work_lane",
            "worktree_binding": "linked",
        },
        ForeignLaneContext(
            current_role="work_lane",
            current_path_scope=("openspec",),
            current_scope_state="bounded",
            candidate_branch="candidate/dev",
            lease=lease,
            root=repo,
        ),
    )
    names = _LEASE_COORDINATES[4:6] + _LEASE_COORDINATES[-3:]
    assert lane["next_action"] == FOREIGN_WORK_LANE_NEXT_ACTION
    assert {name: lease[name] for name in names}.items() <= lane["lease"].items()
    assert lane["action_preview"] == {
        "candidate_actions": ["observe"],
        "blocked_actions": ["write", "land", "retire"],
        "why": ["foreign_lane_requires_handoff_or_exact_authorized_lease_takeover"],
        "mints_authority": False,
        "recheck_required": True,
    }


def test_optional_git_worktree_lock_is_observed_but_never_mints_authority(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    foreign = create_change_source_lane(
        repo,
        tmp_path / "repo-work-locked",
        branch="work/locked",
        holder_ref="agent:test:case:foreign",
    )
    git(repo, "worktree", "lock", "--reason", "handoff-in-progress", foreign.as_posix())
    status = workspace_status(repo)
    lane = next(item for item in status["foreign_work_lanes"] if item["branch"] == "work/locked")
    assert lane["git_lock"] == {
        "locked": True,
        "reason": "handoff-in-progress",
        "mints_authority": False,
    }
    assert lane["action_preview"]["mints_authority"] is False
    assert lane["handoff_required"] is True


def test_unbound_work_lane_ref_preserves_exact_lease_coordinates(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    path = create_change_source_lane(
        repo,
        tmp_path / "repo-work-unbound",
        branch="work/unbound",
        holder_ref="agent:test:case:unbound",
    )
    lease = leases_by_branch(repo)["work/unbound"]
    git(repo, "worktree", "remove", path.as_posix())
    status = workspace_status(repo, include_foreign_path_scope=False)
    binding = next(item for item in status["branch_bindings"] if item["branch"] == "work/unbound")
    unbound = status["unbound_work_lane_refs"]
    assert "coordination" not in status
    assert set(_LEASE_COORDINATES[4:6] + _LEASE_COORDINATES[-3:-1]).isdisjoint(binding)
    assert len(unbound) == 1
    assert {name: unbound[0][name] for name in _LEASE_COORDINATES} == {
        name: lease[name] for name in _LEASE_COORDINATES
    }
    assert validate_schema_instance("workspace-status.schema.json", status, root=repo) == {
        "verdict": "pass",
        "required_gaps": [],
    }


def _mutate_blocked_start(
    case: LaneStartCase,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> str:
    if mutation in {"source-generation", "commitment-generation"}:
        case.commit_source_drift(commitment=mutation.startswith("commitment"))
        return _HOLDER
    if mutation == "candidate-carrier":
        carrier = case.candidate / "openspec/changes/stale/commitment.toml"
        carrier.parent.mkdir(parents=True)
        repository = load_repository_commitment(case.candidate)
        carrier.write_text(
            tomli_w.dumps(
                commitment_fixture(
                    id="change:stale",
                    intent="Stale.",
                    subjects=(repository.id,),
                    scope=("**",),
                ).model_dump(mode="python")
            ),
            encoding="utf-8",
        )
        git(case.candidate, "add", carrier.relative_to(case.candidate).as_posix())
        git(
            case.candidate,
            "commit",
            "-m",
            "seed forbidden candidate carrier",
        )
        return _HOLDER
    if mutation in {"source-during-start", "candidate-during-start"}:
        run_git = lanes.run_git
        drifted = False

        def drift_after_commit(root: Path, *args: str, **kwargs: object):
            nonlocal drifted
            completed = run_git(root, *args, **kwargs)
            if args[:1] == ("commit-tree",) and completed.returncode == 0 and not drifted:
                drifted = True
                target = case.source if mutation.startswith("source") else case.candidate
                commit_fixture_file(target, "DRIFT.md", "drift\n", "drift")
            return completed

        monkeypatch.setattr(lanes, "run_git", drift_after_commit)
        return _HOLDER
    if mutation == "dirty-root":
        (case.repo / "README.md").write_text("# dirty\n", encoding="utf-8")
    elif mutation == "missing-carrier":
        git(case.source, "rm", "-r", "openspec/changes/fixture-change")
    elif mutation == "ambiguous-carrier":
        second = case.source / "openspec/changes/second"
        second.mkdir(parents=True)
        repository = load_repository_commitment(case.source)
        (second / "commitment.toml").write_text(
            tomli_w.dumps(
                commitment_fixture(
                    id="change:second",
                    intent="Second.",
                    subjects=(repository.id,),
                ).model_dump(mode="python")
            ),
            encoding="utf-8",
        )
        (second / "tasks.md").write_text("- [ ] Continue\n", encoding="utf-8")
    return "invalid" if mutation == "invalid-actor" else _HOLDER


@pytest.mark.parametrize(
    ("mutation", "gap"),
    [
        pytest.param(
            "source-generation", "source_lease_head_mismatch", id="source_generation_head"
        ),
        pytest.param(
            "commitment-generation", "source_lease_head_mismatch", id="source_generation_commitment"
        ),
        pytest.param(
            "candidate-carrier",
            "openspec_active_change_unarchived:stale:candidate",
            id="start_work_lane_blocks_candidate_active_change_carrier",
        ),
        pytest.param(
            "source-during-start",
            "source_head_changed_during_lane_start",
            id="start_work_lane_blocks_source_head_drift_before_lease_acquisition",
        ),
        pytest.param(
            "candidate-during-start",
            "candidate_head_changed_during_lane_start",
            id="start_work_lane_blocks_candidate_head_drift_before_lease_acquisition",
        ),
        pytest.param(
            "dirty-root",
            "lane_start_requires_clean_accepted_root",
            id="invalid_source_state_dirty_root",
        ),
        pytest.param(
            "missing-carrier", "source_work_lane_invalid", id="invalid_source_missing_carrier"
        ),
        pytest.param(
            "ambiguous-carrier", "source_work_lane_invalid", id="invalid_source_ambiguous_carrier"
        ),
        pytest.param("invalid-actor", "holder_ref_invalid", id="invalid_actor"),
    ],
)
def test_start_work_lane_prewrite_blocker_claims(
    lane_case: LaneStartCase,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    gap: str,
) -> None:
    holder = _mutate_blocked_start(lane_case, monkeypatch, mutation)
    _assert_absent(lane_case, lane_case.start(holder=holder), gap)


def test_work_lane_status_keeps_committed_binding_and_blocks_dirty_rewrite(
    lane_case: LaneStartCase,
) -> None:
    assert lane_case.start(holder=_HOLDER)["verdict"] == "pass"
    commitment = lane_case.target / "openspec/changes/fixture-change/commitment.toml"
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            "Exercise the governed fixture lifecycle.",
            "Attempt to rewrite the immutable base.",
        ),
        encoding="utf-8",
    )
    status = workspace_status(lane_case.target, include_foreign_path_scope=False)
    assert validate_schema_instance(
        "workspace-status.schema.json", status, root=lane_case.target
    ) == {
        "verdict": "pass",
        "required_gaps": [],
    }
    assert status["closeout_support"]["commitment_binding"] == "bound"
    assert status["closeout_support"]["supported"] is False
    assert status["closeout_support"]["required_gaps"] == ["work_lane_dirty"]


@pytest.mark.parametrize(
    "mode",
    literal_case(
        "lanes.test_lane_family_profile:parametrize:test_start_work_lane_carrier_failure_claims:2"
    ),
)
def test_start_work_lane_carrier_failure_claims(
    lane_case: LaneStartCase,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    run_git = lanes.run_git

    def inject_failure(root: Path, *args: str, **kwargs: object):
        if mode.endswith("worktree_creation_fails") and args[:3] == ("worktree", "add", "--detach"):
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="injected failure")
        completed = run_git(root, *args, **kwargs)
        if (
            mode.endswith("ownership_is_unknown")
            and args[:3] == ("worktree", "list", "--porcelain")
            and ref_head(root, "work/feature")
        ):
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return completed

    monkeypatch.setattr(lanes, "run_git", inject_failure)
    report = lane_case.start(holder=_HOLDER)
    if mode.endswith("worktree_creation_fails"):
        assert report == {
            "verdict": "block",
            "state": "blocked",
            "branch": "work/feature",
            "path": lane_case.target.resolve().as_posix(),
            "stderr": "injected failure",
            "child_process": {
                "argv": ["materialize"],
                "exit_code": 1,
                "stdout": "",
                "stderr": "injected failure",
                "parse_error": "",
            },
            "carrier_cleanup": {"worktree_removed": True, "ref_removed": True},
            "lease_state": "not_acquired",
            "required_gaps": ["worktree_add_failed"],
        }
        lane_case.assert_absent()
    else:
        assert (report["verdict"], report["state"], report["lease_state"]) == (
            "block",
            "blocked",
            "revoked",
        )
        assert report["required_gaps"] == [
            "lane_creation_compensation_failed",
            "lane_start_target_path_ownership_unknown",
        ]
        leases = leases_by_branch(lane_case.repo)
        assert "work/feature" not in leases
        assert leases["work/change-source"]["lease_state"] == "valid"
        assert report["source_lease_state"] == "restored"
        assert ref_head(lane_case.repo, "work/feature")
        assert lane_case.target.exists()
