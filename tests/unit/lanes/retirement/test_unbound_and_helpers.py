from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.shared.core as retirement_shared
import ethos.adapters.mutation.lane_retirement.unbound.core as unbound_retirement
import ethos.adapters.mutation.lane_retirement.unbound.observation.core as unbound_observation
import ethos.adapters.mutation.lane_retirement.unbound.policy.core as unbound_policy
import ethos.adapters.mutation.lane_retirement.unbound.records.core as unbound_records
from ethos.adapters.mutation.lane_lifecycle import core as lane_lifecycle_core
from ethos.adapters.mutation.lane_retirement.unbound.core import retire_unbound_work_lane_ref
from ethos.adapters.repo.dirty.core import dirty_provenance
from ethos.adapters.store.state.lease.lifecycle import core as state
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

_CLAIM_ID = "exceptional-unbound-test-claim"
_CHRONICLE_REF = "evidence/chronicle/exceptional-unbound-test/2026-07-19.md"
_OBSERVE = "_" + "observe"


def _commit(repo: Path, message: str) -> None:
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )


def _exceptional_fixture(tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    branch = "work/stale-ref"
    git(repo, "branch", branch, "dev")
    head = git(repo, "rev-parse", branch)
    claim = repo / "evidence" / "claims" / f"{_CLAIM_ID}.toml"
    claim.parent.mkdir(parents=True)
    claim.write_text(
        "\n".join(
            (
                "[claim]",
                f'id = "{_CLAIM_ID}"',
                'subject = "ethos:test:exceptional-unbound"',
                'state = "active"',
                'summary = "Test-only accepted exceptional-retirement policy claim."',
                "",
            )
        ),
        encoding="utf-8",
    )
    chronicle = repo / _CHRONICLE_REF
    chronicle.parent.mkdir(parents=True)
    chronicle.write_text(
        "\n".join(
            (
                "# Exceptional unbound test policy",
                "",
                "event: lane_retire/unbound_exceptional",
                f"target_branch: {branch}",
                f"target_head: {head}",
                f"target_claim: {_CLAIM_ID}",
                "",
            )
        ),
        encoding="utf-8",
    )
    _commit(repo, "accept exceptional unbound test policy")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    return repo, branch, head, _CHRONICLE_REF


def test_retire_unbound_work_lane_ref_requires_accepted_chronicle(
    tmp_path: Path,
) -> None:
    repo, branch, head, _chronicle = _exceptional_fixture(tmp_path)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="accepted truth already contains the source",
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["head"] == head
    assert report["mutation"]["request"] == {
        "command": "lane-retire-unbound",
        "apply": False,
        "confirmation_present": False,
        "expect_head": head,
    }
    assert report["mutation"]["ref"] == f"refs/heads/{branch}"
    assert report["mutation"]["decision"]["verdict"] == "block"
    assert report["required_gaps"] == ["unbound_retire_chronicle_ref_required"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_plans_exact_accepted_policy(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="accepted truth already contains the source",
        chronicle_ref=chronicle,
    )

    assert report["ok"] is True
    assert report["state"] == "ready_to_retire_unbound_exceptional"
    assert report["required_gaps"] == []
    assert report["observation"]["chronicle"]["byte_identical_to_accepted"] is True
    assert report["observation"]["chronicle"]["claim_byte_identical_to_accepted"] is True
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_apply_requires_all_exceptional_controls(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="accepted truth already contains the source",
        chronicle_ref=chronicle,
        apply=True,
        authorized=True,
    )

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [
        "irreversible_confirmation_required",
        "unbound_retire_requires_break_glass",
    ]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_blocks_head_mismatch(tmp_path: Path) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head="0" * 40,
        reason="accepted truth already contains the source",
        chronicle_ref=chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["ok"] is False
    assert "expect_head_mismatch" in report["required_gaps"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_blocks_linked_worktree(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-linked"
    git(repo, "worktree", "add", "-b", "work/linked", worktree.as_posix(), "dev")
    head = git(repo, "rev-parse", "work/linked")

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/linked",
        expect_head=head,
        reason="must preserve linked worktree",
    )

    assert report["ok"] is False
    assert "unbound_retire_ref_not_unbound" in report["required_gaps"]
    assert worktree.exists()


def test_retire_unbound_work_lane_ref_requires_reason_authorization_and_head(
    tmp_path: Path,
) -> None:
    repo, branch, _head, chronicle = _exceptional_fixture(tmp_path)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        chronicle_ref=chronicle,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "authorization_required",
        "expect_head_required",
        "irreversible_confirmation_required",
        "retire_reason_required",
        "unbound_retire_requires_break_glass",
    ]


def test_lane_retirement_repo_root_falls_back_when_git_root_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fail_git(_root: Path, *args: str, _check: bool = True):
        assert args == ("rev-parse", "--show-toplevel")
        raise subprocess.CalledProcessError(128, ["git", *args])

    monkeypatch.setattr(lane_lifecycle_core, "run_git", fail_git)

    assert lane_lifecycle_core.repo_root(tmp_path) == tmp_path.resolve()


def test_retire_unbound_work_lane_ref_does_not_attempt_delete_without_all_controls(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    real_git = unbound_retirement.run_git
    attempted_delete = False

    def fake_git(root: Path, *args: str, check: bool = True):
        nonlocal attempted_delete
        if args[:2] == ("update-ref", "-d"):
            attempted_delete = True
        return real_git(root, *args, check=check)

    monkeypatch.setattr(unbound_retirement, "run_git", fake_git)

    report = unbound_retirement.retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="accepted truth already contains the source",
        chronicle_ref=chronicle,
        apply=True,
        authorized=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "irreversible_confirmation_required",
        "unbound_retire_requires_break_glass",
    ]
    assert attempted_delete is False
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_classifies_branch_input_gaps(
    tmp_path: Path,
) -> None:
    repo = init_repo(tmp_path / "repo")
    git(repo, "branch", "main", "dev")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    git(repo, "branch", "topic", "dev")

    missing_branch = retire_unbound_work_lane_ref(
        root=repo,
        branch="",
        expect_head="h",
        reason="cleanup",
    )
    assert "unbound_retire_branch_required" in missing_branch["required_gaps"]

    not_found = retire_unbound_work_lane_ref(
        root=repo,
        branch="work/missing",
        expect_head="h",
        reason="cleanup",
    )
    assert "unbound_retire_branch_not_found" in not_found["required_gaps"]

    wrong_role = retire_unbound_work_lane_ref(
        root=repo,
        branch="topic",
        expect_head=git(repo, "rev-parse", "topic"),
        reason="cleanup",
    )
    assert "unbound_retire_not_work_lane" in wrong_role["required_gaps"]


def test_retire_unbound_work_lane_ref_blocks_unaccepted_chronicle(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    path = repo / chronicle
    path.write_text(
        path.read_text(encoding="utf-8").replace("target_head", "target_missing_head"),
        encoding="utf-8",
    )

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="accepted truth already contains the source",
        chronicle_ref=chronicle,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["unbound_retire_chronicle_content_drift"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_blocks_active_lease(tmp_path: Path) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    state.acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject=branch,
        holder_ref="agent:test:case:lease-holder",
        payload={"branch": branch, "expected_head": head},
    )

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="must preserve a currently leased target",
        chronicle_ref=chronicle,
        apply=True,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["unbound_retire_active_lease"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_applies_only_to_exact_accepted_policy(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="accepted truth already contains the exact source",
        chronicle_ref=chronicle,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is True
    assert report["state"] == "retired_unbound_exceptional"
    assert report["effect"]["command"] == "git update-ref -d"
    assert report["receipt"]["postconditions"] == {
        "active_lease_absent": True,
        "chronicle_unchanged": True,
        "protected_refs_unchanged": True,
        "ref_absent": True,
        "unbound_absent": True,
    }
    assert Path(str(report["attempt_path"])).is_file()
    assert Path(str(report["receipt_path"])).is_file()
    assert (
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    )


def test_retire_unbound_work_lane_ref_blocks_pre_effect_observation_drift(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    real_observe = getattr(unbound_retirement, _OBSERVE)
    observation_count = 0

    def drifting_observe(repo_root: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
        nonlocal observation_count
        observation_count += 1
        observation = real_observe(repo_root, branch=branch, chronicle_ref=chronicle_ref)
        if observation_count == 2:
            protected = dict(observation["protected_refs"])
            protected["candidate/dev"] = "f" * 40
            observation["protected_refs"] = protected
        return observation

    monkeypatch.setattr(unbound_retirement, "_observe", drifting_observe)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="must stop when a protected binding drifts",
        chronicle_ref=chronicle,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["unbound_retire_pre_effect_observation_stale"]
    assert Path(str(report["attempt_path"])).is_file()
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_detects_post_effect_ref_nonremoval(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    real_git = unbound_retirement.run_git

    def no_effect_git(root: Path, *args: str, check: bool = True):
        if args[:2] == ("update-ref", "-d"):
            return subprocess.CompletedProcess(["git", *args], 0, "", "")
        return real_git(root, *args, check=check)

    monkeypatch.setattr(unbound_retirement, "run_git", no_effect_git)

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="must verify the observed postcondition",
        chronicle_ref=chronicle,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "unbound_retire_ref_remove_not_observed",
        "unbound_retire_status_postcondition_not_observed",
    ]
    assert Path(str(report["attempt_path"])).is_file()
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_retire_unbound_work_lane_ref_blocks_collision_before_effect(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    observe = getattr(unbound_retirement, _OBSERVE)
    before = observe(repo, branch=branch, chronicle_ref=chronicle)
    operation_id = unbound_records.operation_id(
        branch=branch,
        expect_head=head,
        accepted_head=str(before["accepted_head"]),
        protected_refs=before["protected_refs"],
        claim_id=str(before["claim_id"]),
        chronicle=unbound_observation.chronicle_binding(before),
        reason="must reject a pre-existing mismatched attempt",
        observation_sha256=str(before["observation_sha256"]),
    )
    payload = unbound_records.attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=head,
        reason="different valid attempt payload",
        observation=before,
    )
    records_root = repo.parent / f"{repo.name}-records"
    unbound_records.write_record(
        unbound_records.attempt_path(records_root, operation_id),
        payload,
        kind=unbound_records.ATTEMPT_KIND,
    )

    report = retire_unbound_work_lane_ref(
        root=repo,
        branch=branch,
        expect_head=head,
        reason="must reject a pre-existing mismatched attempt",
        chronicle_ref=chronicle,
        authorized=True,
        break_glass=True,
        confirm_irreversible=True,
        apply=True,
    )

    assert report["ok"] is False
    assert report["required_gaps"] == ["unbound_retire_record_collision"]
    assert git(repo, "rev-parse", "--verify", branch) == head


def test_lane_retirement_handles_malformed_status_fragments() -> None:
    assert unbound_observation.unbound_work_lane_ref({}, "work/x") is None
    assert (
        unbound_observation.unbound_work_lane_ref(
            {"coordination": {"unbound_work_lane_refs": {}}}, "work/x"
        )
        is None
    )
    assert unbound_observation.branch_binding({}, "work/x") is None
    assert unbound_observation.branch_binding({"branch_bindings": {}}, "work/x") is None


def test_dirty_provenance_lives_in_semantic_subpackage(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "new.txt").write_text("new\n", encoding="utf-8")

    report = dirty_provenance(repo)

    assert report["dirty"] is True
    assert report["summary"]["untracked"] == 1


def test_delete_json_projection_lease_ignores_absent_or_malformed_projection(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0

    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text("{not-json", encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0

    lease_path.write_text(json.dumps([{"branch": "work/landed"}]), encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0

    lease_path.write_text(json.dumps({"leases": "not-a-list"}), encoding="utf-8")
    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0


def test_delete_json_projection_lease_matches_branch_or_subject_and_preserves_rows(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "leases": [
                    {"subject": "work/landed", "owner": "agent-subject"},
                    {"branch": "work/other", "owner": "agent-other"},
                    "opaque-row",
                ],
            }
        ),
        encoding="utf-8",
    )

    removed = retirement_shared.delete_json_projection_lease(repo, subject="work/landed")

    assert removed == 1
    payload = json.loads(lease_path.read_text(encoding="utf-8"))
    assert payload == {
        "leases": [
            {"branch": "work/other", "owner": "agent-other"},
            "opaque-row",
        ],
        "schema_version": 1,
    }


def test_delete_json_projection_lease_leaves_projection_when_subject_is_absent(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    lease_path = repo / ".cache" / "local-state" / "worktree" / "leases.json"
    lease_path.parent.mkdir(parents=True)
    original = {"leases": [{"branch": "work/other", "owner": "agent-other"}]}
    lease_path.write_text(json.dumps(original), encoding="utf-8")

    assert retirement_shared.delete_json_projection_lease(repo, subject="work/landed") == 0
    assert json.loads(lease_path.read_text(encoding="utf-8")) == original


def test_exceptional_retirement_observation_edges_are_fail_closed(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    chronicle_ref = "evidence/chronicle/test/2026-07-19.md"
    chronicle = repo / chronicle_ref
    chronicle.parent.mkdir(parents=True)
    chronicle.mkdir()

    directory = unbound_observation.chronicle_observation(
        repo,
        accepted_branch="dev",
        chronicle_ref=chronicle_ref,
    )
    assert directory[unbound_observation.HAS_LOCAL_CHRONICLE] is False
    chronicle.rmdir()
    chronicle.write_text("event: lane_retire/unbound_exceptional\n", encoding="utf-8")

    monkeypatch.setattr(
        unbound_observation.os, "lstat", lambda _path: (_ for _ in ()).throw(OSError())
    )
    unreadable = unbound_observation.chronicle_observation(
        repo,
        accepted_branch="dev",
        chronicle_ref=chronicle_ref,
    )
    assert unreadable[unbound_observation.HAS_LOCAL_CHRONICLE] is False
    monkeypatch.undo()

    monkeypatch.setattr(unbound_observation, "git_show_bytes", lambda *_args: None)
    unaccepted = unbound_observation.chronicle_observation(
        repo,
        accepted_branch="dev",
        chronicle_ref=chronicle_ref,
    )
    assert unaccepted[unbound_observation.HAS_LOCAL_CHRONICLE] is True
    assert unaccepted[unbound_observation.HAS_ACCEPTED_CHRONICLE] is False
    assert unbound_observation.chronicle_fields(b"\xff") == {}
    assert unbound_observation.chronicle_path(repo, "") is None
    assert unbound_observation.chronicle_path(repo, "/outside") is None
    assert unbound_observation.chronicle_path(repo, "evidence/chronicle/../escape") is None

    monkeypatch.setattr(Path, "resolve", lambda _path: (_ for _ in ()).throw(OSError()))
    assert unbound_observation.chronicle_path(repo, chronicle_ref) is None
    monkeypatch.undo()

    assert (
        unbound_observation.claim_observation(
            repo,
            accepted_branch="dev",
            claim_id="../invalid",
        )[unbound_observation.HAS_LOCAL_CLAIM]
        is False
    )
    claim = repo / "evidence/claims/test.toml"
    claim.parent.mkdir(parents=True)
    claim.mkdir()
    assert (
        unbound_observation.claim_observation(
            repo,
            accepted_branch="dev",
            claim_id="test",
        )[unbound_observation.HAS_LOCAL_CLAIM]
        is False
    )
    claim.rmdir()
    claim.write_bytes(b"\xff")
    assert (
        unbound_observation.claim_observation(
            repo,
            accepted_branch="dev",
            claim_id="test",
        )[unbound_observation.HAS_LOCAL_CLAIM]
        is False
    )
    claim.write_text('[claim]\nid = "test"\nstate = "active"\n', encoding="utf-8")
    missing_accepted_claim = unbound_observation.claim_observation(
        repo,
        accepted_branch="dev",
        claim_id="test",
    )
    assert missing_accepted_claim[unbound_observation.HAS_LOCAL_CLAIM] is True
    assert missing_accepted_claim[unbound_observation.HAS_ACCEPTED_CLAIM] is False


def test_exceptional_retirement_policy_helpers_cover_every_fail_closed_outcome(
    tmp_path: Path,
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    observed = unbound_observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    unavailable = {**observed, "protected_refs": {"main": "", "dev": head}}
    assert "unbound_retire_protected_ref_unavailable" in unbound_policy.admission_gaps(
        repo,
        branch=branch,
        expect_head=head,
        reason="must require protected refs",
        apply=False,
        authorized=False,
        break_glass=False,
        confirm_irreversible=False,
        observed=unavailable,
    )
    assert unbound_policy.target_gaps(
        {"event": "", "target_branch": "", "target_head": ""},
        branch=branch,
        head=head,
    ) == ["unbound_retire_chronicle_event_missing"]
    assert unbound_policy.target_gaps(
        {
            "event": unbound_policy.EVENT,
            "target_branch": "work/other",
            "target_head": "other",
        },
        branch=branch,
        head=head,
    ) == ["unbound_retire_chronicle_target_mismatch"]

    assert unbound_policy.accepted_control_root({}, accepted_head=head)[1] == (
        "unbound_retire_accepted_control_root_unavailable"
    )
    assert (
        unbound_policy.accepted_control_root({"worktrees": [object()]}, accepted_head=head)[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )
    assert (
        unbound_policy.accepted_control_root(
            {"worktrees": [{"role": unbound_policy.ROLE_ACCEPTED_ROOT, "path": ""}]},
            accepted_head=head,
        )[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )
    assert (
        unbound_policy.accepted_control_root(
            {
                "worktrees": [
                    {
                        "role": unbound_policy.ROLE_ACCEPTED_ROOT,
                        "path": (tmp_path / "missing").as_posix(),
                    }
                ]
            },
            accepted_head=head,
        )[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )
    accepted_head = git(repo, "rev-parse", "dev")
    accepted_status = {
        "worktrees": [{"role": unbound_policy.ROLE_ACCEPTED_ROOT, "path": repo.as_posix()}]
    }
    assert unbound_policy.accepted_control_root(accepted_status, accepted_head="0" * 40)[1] == (
        "unbound_retire_accepted_control_root_stale"
    )
    control_root, gap = unbound_policy.accepted_control_root(
        accepted_status, accepted_head=accepted_head
    )
    assert control_root == repo.resolve()
    assert gap == ""
    assert (
        unbound_policy.accepted_control_root(
            {"worktrees": [{"role": "work_lane", "path": repo.as_posix()}]}, accepted_head=head
        )[1]
        == "unbound_retire_accepted_control_root_unavailable"
    )

    before = {
        "protected_refs": {"main": head},
        "chronicle": {"ref": "before"},
    }
    after = {
        "protected_refs": {"main": "other"},
        "chronicle": {"ref": "after"},
        "head": head,
        "status_unbound": True,
        "worktree_binding": "unbound",
        unbound_observation.HAS_ACTIVE_LEASE: True,
    }
    deleted = subprocess.CompletedProcess(["git", "update-ref"], 1, "", "failed")
    assert unbound_policy.post_effect_gaps(before=before, after=after, deleted=deleted) == [
        "unbound_retire_active_lease",
        "unbound_retire_chronicle_changed",
        "unbound_retire_protected_refs_changed",
        "unbound_retire_ref_delete_failed",
        "unbound_retire_ref_remove_not_observed",
        "unbound_retire_status_postcondition_not_observed",
    ]


def test_exceptional_retirement_records_cover_idempotence_races_and_invalid_payloads(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    before = unbound_observation.observe(repo, branch=branch, chronicle_ref=chronicle)
    operation_id = unbound_records.operation_id(
        branch=branch,
        expect_head=head,
        accepted_head=str(before["accepted_head"]),
        protected_refs=before["protected_refs"],
        claim_id=str(before["claim_id"]),
        chronicle=unbound_observation.chronicle_binding(before),
        reason="coverage record",
        observation_sha256=str(before["observation_sha256"]),
    )
    payload = unbound_records.attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=head,
        reason="coverage record",
        observation=before,
    )
    record = tmp_path / "record.json"
    assert unbound_records.write_record(record, payload, kind=unbound_records.ATTEMPT_KIND) == (
        record.as_posix()
    )
    assert unbound_records.write_record(record, payload, kind=unbound_records.ATTEMPT_KIND) == (
        record.as_posix()
    )
    collision = {**payload, "reason": "different valid record"}
    record.write_text(json.dumps(collision), encoding="utf-8")
    with pytest.raises(ValueError, match="unbound_retire_record_collision"):
        unbound_records.write_record(record, payload, kind=unbound_records.ATTEMPT_KIND)

    def race_equal(_source: Path, destination: Path) -> None:
        destination.write_text(json.dumps(payload), encoding="utf-8")
        raise FileExistsError

    equal_race = tmp_path / "equal-race.json"
    monkeypatch.setattr(unbound_records.os, "link", race_equal)
    assert unbound_records.write_record(equal_race, payload, kind=unbound_records.ATTEMPT_KIND) == (
        equal_race.as_posix()
    )

    def race_collision(_source: Path, destination: Path) -> None:
        destination.write_text(json.dumps(collision), encoding="utf-8")
        raise FileExistsError

    monkeypatch.setattr(unbound_records.os, "link", race_collision)
    with pytest.raises(ValueError, match="unbound_retire_record_collision"):
        unbound_records.write_record(
            tmp_path / "collision-race.json",
            payload,
            kind=unbound_records.ATTEMPT_KIND,
        )
    monkeypatch.undo()

    with pytest.raises(ValueError, match="unbound_retire_record_unsafe"):
        unbound_records.read_record(tmp_path, kind=unbound_records.ATTEMPT_KIND)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        unbound_records.read_record(malformed, kind=unbound_records.ATTEMPT_KIND)
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="unbound_retire_record_invalid"):
        unbound_records.read_record(malformed, kind=unbound_records.ATTEMPT_KIND)

    invalid_cases = (
        {},
        {**payload, "operation_id": "wrong"},
        {**payload, "branch": "topic"},
        {**payload, "expected_head": "short"},
        {**payload, "mints_authority": True},
        {**payload, "protected_refs": {}},
    )
    for invalid in invalid_cases:
        with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
            unbound_records.validate_record(invalid, kind=unbound_records.ATTEMPT_KIND)

    receipt = {
        **{key: value for key, value in payload.items() if key != "protected_refs"},
        "kind": unbound_records.RECEIPT_KIND,
        "protected_refs_before": payload["protected_refs"],
        "protected_refs_after": before["protected_refs"],
        "after_observation_sha256": "a" * 64,
        "postconditions": {
            "ref_absent": True,
            "unbound_absent": True,
            "active_lease_absent": True,
            "protected_refs_unchanged": True,
            "chronicle_unchanged": True,
        },
    }
    unbound_records.validate_record(receipt, kind=unbound_records.RECEIPT_KIND)
    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        unbound_records.validate_record(
            {**receipt, "postconditions": {"ref_absent": False}},
            kind=unbound_records.RECEIPT_KIND,
        )
    with pytest.raises(ValueError, match="unbound_retire_record_invalid"):
        unbound_records.validate_record(
            {**receipt, "protected_refs_after": {"main": "changed"}},
            kind=unbound_records.RECEIPT_KIND,
        )


def test_exceptional_retirement_covers_control_root_and_receipt_write_failures(
    monkeypatch, tmp_path: Path
) -> None:
    repo, branch, head, chronicle = _exceptional_fixture(tmp_path)
    controls = {
        "root": repo,
        "branch": branch,
        "expect_head": head,
        "reason": "coverage control root",
        "chronicle_ref": chronicle,
        "authorized": True,
        "break_glass": True,
        "confirm_irreversible": True,
        "apply": True,
    }
    monkeypatch.setattr(
        unbound_policy,
        "accepted_control_root",
        lambda *_args, **_kwargs: (None, "unbound_retire_accepted_control_root_unavailable"),
    )
    blocked = retire_unbound_work_lane_ref(**controls)
    assert blocked["required_gaps"] == ["unbound_retire_accepted_control_root_unavailable"]
    monkeypatch.undo()

    real_write = unbound_records.write_record

    def fail_receipt(path: Path, payload: dict[str, object], *, kind: str) -> str:
        if kind == unbound_records.RECEIPT_KIND:
            raise OSError("receipt write failure")
        return real_write(path, payload, kind=kind)

    monkeypatch.setattr(unbound_records, "write_record", fail_receipt)
    receipt_failure = retire_unbound_work_lane_ref(**controls)
    assert receipt_failure["required_gaps"] == ["receipt write failure"]
