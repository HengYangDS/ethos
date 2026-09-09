from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
import ethos.adapters.mutation.lane_retirement.linked_effect as linked_effect
import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
from ethos.contracts.retirement import LinkedRetirementRequest
from ethos.contracts.retirement import RetirementOperation
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.lane_scenarios import superseded_work_lane
from tests.support.lifecycle_cases import assert_public_decision
from tests.support.lifecycle_cases import strict_lease
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.semantic import commitment_fixture

BRANCH = "work/superseded"
ACTOR = "agent:test:case:retirement"


def _retirement_request(
    head: str, absorbed_by: str, *, apply: bool = False
) -> LinkedRetirementRequest:
    return LinkedRetirementRequest(
        branch=BRANCH,
        expect_head=head,
        absorbed_by=absorbed_by,
        reason="accepted tree contains the obsolete delta",
        authorize=True,
        apply=apply,
    )


def _assert_retired(repo: Path, source: Path, database: Path) -> None:
    assert (
        source.exists(),
        git(repo, "branch", "--list", BRANCH),
        observe_lease(database, BRANCH).state,
    ) == (False, "", "missing")


def _lane(
    *,
    branch: str = "work/source",
    path: str = "/lane",
    head: str = "a" * 40,
    holder: str = "agent:test:holder",
) -> dict[str, object]:
    return {
        "branch": branch,
        "path": path,
        "head": head,
        "lease_state": "valid",
        "lease": {
            "generation": 1,
            "holder_ref": holder,
            "expires_at": "2026-08-11T00:00:00+00:00",
        },
    }


def test_superseded_plan_preserves_proof_commitment_and_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    lane = _lane()
    authority = {
        **_lane(),
        "branch": "work/successor",
        "head": "c" * 40,
        "path": "/successor",
    }
    commitment = commitment_fixture(id="change:successor")

    monkeypatch.setattr(Path, "is_dir", lambda path: path == Path("/successor"))
    monkeypatch.setattr(linked_effect, "proof_attestation", lambda *_args: object())
    monkeypatch.setattr(
        linked_effect,
        "plan_from_statement",
        lambda _proof: SimpleNamespace(commitment=commitment.model_dump(mode="json")),
    )

    def compile_plan(
        _root: Path,
        selected_commitment: object,
        _effect: object,
        **kwargs: object,
    ) -> object:
        captured["commitment"] = selected_commitment
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(linked_effect, "compile_observed_git_effect", compile_plan)

    transaction_root, plan = linked_effect.linked_retirement_plan(
        Path("/control"),
        lane,
        accepted=("dev", "b" * 40),
        authority=authority,
        mode="superseded",
        actor=ACTOR,
        worktree_clean=True,
    )

    assert transaction_root == Path("/successor")
    assert plan is not None
    assert captured["commitment"] == commitment
    policy, values = captured["policy"], captured["values"]
    assert isinstance(policy, dict)
    assert isinstance(values, dict)
    assert policy["retirement_mode"] == "superseded"
    assert values["lease_generation"] == {
        "lane_ref": "work/successor",
        "generation": 1,
        "holder_ref": "agent:test:holder",
        "expires_at": "2026-08-11T00:00:00+00:00",
    }


@pytest.mark.parametrize("lease_state", ["valid", "expired", "missing"])
def test_landed_plan_binds_and_admits_exact_git_and_lease_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lease_state: str
) -> None:
    """Compile real effects without proof reads or a simulated plan compiler."""
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root)
    git(root, "add", ".ethos/profile.toml")
    git(root, "commit", "-m", "declare repository identity")
    head = git(root, "rev-parse", "HEAD")
    git(root, "branch", "work/source", head)
    lane = _lane(path=(tmp_path / "lane").as_posix(), head=head)
    lane.update(lease_state=lease_state, lease={"mints_authority": False})
    expected = {
        "refs": {"refs/heads/work/source": head},
        "assertions": {"refs/heads/dev": head},
        "linked_worktree": {"path": lane["path"], "clean": True},
        "target_lease_state": lease_state,
    }
    if lease_state != "missing":
        record = acquire_lease(
            state_database(root),
            lease=strict_lease(
                branch="work/source",
                holder=ACTOR if lease_state == "valid" else "agent:test:case:former-holder",
                expires_at=datetime.now(UTC) + timedelta(days=1 if lease_state == "valid" else -1),
            ),
        )
        lane["lease"] = {key: record[key] for key in ("holder_ref", "generation", "expires_at")}
        expected.update(
            lease_generation={"lane_ref": "work/source", **lane["lease"]},
            lease_generation_state=lease_state,
        )
    monkeypatch.setenv("ETHOS_ACTOR", ACTOR)
    monkeypatch.setattr(
        linked_effect,
        "proof_attestation",
        lambda *_args: pytest.fail("landed retirement must not read proof"),
    )

    transaction_root, plan = linked_effect.linked_retirement_plan(
        root,
        lane,
        accepted=("dev", head),
        authority=lane,
        mode="landed",
        actor=ACTOR,
        worktree_clean=True,
    )

    assert transaction_root == root
    assert plan.commitment is None
    assert plan.request["subject"] == plan.authority["subject"] == "work/source"
    assert plan.authority["actor"] == ACTOR
    assert plan.policy["retirement_mode"] == "landed"
    assert (
        not {"branch", "accepted_branch", "accepted_head", "authority_branch", "authority_head"}
        & plan.policy.keys()
    )
    assert plan.facts["values"] == expected
    admit_git_effect(root, plan)


@pytest.mark.parametrize(
    ("merge_base", "changed", "returncode", "expected"),
    [
        (None, None, 0, False),
        ("base", None, 0, False),
        ("base", "", 1, True),
        ("base", "a\0", 1, False),
    ],
)
def test_absorbed_handles_unavailable_and_semantic_delta_results(
    monkeypatch: pytest.MonkeyPatch,
    merge_base: str | None,
    changed: str | None,
    returncode: int,
    expected: int,
) -> None:
    def output(_repo: Path, *args: str) -> str | None:
        return merge_base if args[0] == "merge-base" else changed

    monkeypatch.setattr(effects, "output", output)
    monkeypatch.setattr(
        effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, "", ""),
    )

    assert effects.absorbed(Path("/repo"), "head", "accepted") is bool(expected)


@pytest.mark.parametrize(
    ("ancestor", "paths", "archives", "blobs", "expected"),
    [
        (True, (), (), {}, {}),
        (False, (), (), {}, {}),
        (True, ("src/x.py",), ("archive/x",), {}, {}),
        (
            True,
            ("openspec/changes/x/proposal.md",),
            (),
            {},
            {},
        ),
        (
            True,
            ("openspec/changes/x/proposal.md",),
            ("openspec/changes/archive/2026-08-10-x",),
            {"source": "blob-a", "target": "blob-b"},
            {},
        ),
    ],
)
def test_archive_absorption_rejects_ambiguous_or_nonidentical_carriers(
    monkeypatch: pytest.MonkeyPatch,
    ancestor: int,
    paths: tuple[str, ...],
    archives: tuple[str, ...],
    blobs: dict[str, str],
    expected: dict[str, object],
) -> None:
    monkeypatch.setattr(effects, "is_ancestor", lambda *_args: ancestor)
    monkeypatch.setattr(effects, "_carrier_delta_paths", lambda *_args: paths)
    monkeypatch.setattr(effects, "_archive_roots", lambda *_args: archives)

    def output(_repo: Path, _command: str, subject: str) -> str:
        return blobs.get("source" if subject.startswith("head:") else "target", "")

    monkeypatch.setattr(effects, "output", output)

    assert (
        effects.archived_carrier_absorption(Path("/repo"), head="head", accepted_head="accepted")
        == expected
    )


@pytest.mark.parametrize("boundary", ["checkout", "archive"])
def test_effect_gaps_recheck_successor_checkout_and_archive_mapping(monkeypatch, boundary):
    lane = {**_lane(), "archive_absorption": {"change": "x"}}
    authority = _lane(branch="work/authority", path="/authority", head="c" * 40)
    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:holder")
    monkeypatch.setattr(
        effects,
        "output",
        lambda root, *args: (
            ("dev" if root == Path("/control") else "work/authority")
            if args[0] == "symbolic-ref"
            else "b" * 40
        ),
    )
    monkeypatch.setattr(effects, "reobservation_gaps", lambda *_args: [])
    monkeypatch.setattr(effects, "archived_carrier_absorption", lambda *_a, **_k: {})
    gaps = effects.effect_gaps(
        Path("/wrong" if boundary == "checkout" else "/authority"),
        Path("/control"),
        mode="superseded",
        policy=BranchRolePolicy(),
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )
    assert gaps == [
        "retirement_authority_checkout_stale"
        if boundary == "checkout"
        else "retirement_archive_absorption_stale"
    ]


@pytest.mark.parametrize("failure", ["none", "before-delete", "after-delete"])
@pytest.mark.parametrize("unbound", [False, True])
def test_superseded_retirement_recovers_observed_effects_without_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str, *, unbound: bool
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(tmp_path, holder_ref=holder)
    install_fixture_hook_runtime(repo)
    if unbound:
        git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    request = _retirement_request(head, accepted).model_copy(update={"path": lane.as_posix()})
    planned = retire_linked_work_lane(root=repo, mode="superseded", request=request)
    assert_public_decision(planned, verdict="pass", state="ready_to_retire_superseded", gaps=[])
    planned_lane = planned["lane"]
    assert isinstance(planned_lane, dict)
    assert bool(planned_lane.get("recovery_required")) is unbound
    assert lane.exists() is not unbound
    before_lease = observe_lease(database, BRANCH).record()
    delete = operation.delete_operation_ref

    def fail_delete(root: Path, request: RetirementOperation) -> None:
        if failure == "after-delete":
            delete(root, request)
        message = "retirement_delete_interrupted"
        raise ValueError(message)

    if failure != "none":
        monkeypatch.setattr(operation, "delete_operation_ref", fail_delete)
    report = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )
    if failure == "none":
        assert_public_decision(report, verdict="pass", state="retired", gaps=[])
        assert "recovery" not in report
        _assert_retired(repo, lane, database)
        return
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["retirement_delete_interrupted"]
    assert not lane.exists()
    deleted = failure == "after-delete"
    assert report["state"] == ("partial_transition" if not unbound or deleted else "blocked")
    assert report["completed_effects"] == (
        ([] if unbound else ["remove_worktree"]) + (["delete_ref"] if deleted else [])
    )
    assert report["remaining_effects"] == (
        ["revoke_lease"] if deleted else ["delete_ref", "revoke_lease"]
    )
    assert "ethos lane retire recover" in str(report["next_action"])
    assert git(repo, "for-each-ref", "--format=%(objectname)", f"refs/heads/{BRANCH}") == (
        "" if deleted else head
    )
    assert observe_lease(database, BRANCH).record() == before_lease
    assert git(repo, "rev-parse", "dev") == accepted
    receipt = report["receipt"]
    assert isinstance(receipt, dict)

    def already_completed(*_args: object) -> None:
        pytest.fail("recovery replayed a completed effect")

    monkeypatch.setattr(operation, "remove_operation_worktree", already_completed)
    monkeypatch.setattr(operation, "delete_operation_ref", already_completed if deleted else delete)
    for _ in range(2):
        recovered = operation.execute_retirement_operation(
            root=repo,
            receipt_path=str(receipt["path"]),
            receipt_sha256=str(receipt["sha256"]),
            apply=True,
            authorized=True,
        )
        assert recovered["state"] == "retired", recovered
        assert recovered["remaining_effects"] == []
        _assert_retired(repo, lane, database)
        monkeypatch.setattr(operation, "delete_operation_ref", already_completed)
        monkeypatch.setattr(operation, "revoke_operation_lease", already_completed)


@pytest.mark.parametrize(
    ("scenario", "gap"),
    [
        ("path-collision", "retirement_recovery_path_collision"),
        ("foreign-holder", "foreign_work_lane_retire_authority_required"),
    ],
)
def test_superseded_retirement_partial_recovery_rejects_stale_exact_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
    gap: str,
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(
        tmp_path / scenario, holder_ref=holder
    )
    git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv(
        "ETHOS_ACTOR",
        "agent:test:case:foreign" if scenario == "foreign-holder" else holder,
    )
    if scenario == "path-collision":
        lane.mkdir()
    request = _retirement_request(head, accepted).model_copy(update={"path": lane.as_posix()})

    report = retire_linked_work_lane(root=repo, mode="superseded", request=request)

    assert report["verdict"] == "block"
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert gap in gaps
    assert git(repo, "rev-parse", BRANCH) == head
    assert observe_lease(database, BRANCH).state == "valid"
