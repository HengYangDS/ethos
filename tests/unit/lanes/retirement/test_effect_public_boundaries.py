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
from ethos.adapters.mutation.lane_retirement.linked import LinkedRetirementRequest
from ethos.adapters.mutation.lane_retirement.linked import retire_linked_work_lane
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import BranchRolePolicy
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


def test_landed_plan_is_commitment_free_and_does_not_read_proof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    lane = _lane()

    monkeypatch.setattr(Path, "is_dir", lambda _path: False)
    monkeypatch.setattr(
        linked_effect,
        "proof_attestation",
        lambda *_args: pytest.fail("landed retirement must not read proof"),
    )

    def compile_plan(
        _root: Path,
        commitment: object,
        _effect: object,
        **kwargs: object,
    ) -> object:
        captured["commitment"] = commitment
        policy = kwargs["policy"]
        assert isinstance(policy, dict)
        captured["policy"] = policy
        captured["retirement_mode"] = policy["retirement_mode"]
        captured["values"] = kwargs["values"]
        return object()

    monkeypatch.setattr(linked_effect, "compile_observed_git_effect", compile_plan)

    _root, plan = linked_effect.linked_retirement_plan(
        Path("/control"),
        lane,
        accepted=("dev", "b" * 40),
        authority=lane,
        mode="landed",
        actor=ACTOR,
        worktree_clean=True,
    )

    assert plan is not None
    assert captured["commitment"] is None
    assert captured["retirement_mode"] == "landed"
    assert captured["policy"]["actor"] == ACTOR
    assert captured["policy"]["subject"] == "work/source"
    assert captured["values"] == {
        "linked_worktree": {"path": "/lane", "clean": True},
        "target_lease_state": "valid",
        "lease_generation": {
            "lane_ref": "work/source",
            "generation": 1,
            "holder_ref": "agent:test:holder",
            "expires_at": "2026-08-11T00:00:00+00:00",
        },
        "lease_generation_state": "valid",
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
    assert captured["policy"]["retirement_mode"] == "superseded"
    assert captured["values"]["lease_generation"] == {
        "lane_ref": "work/successor",
        "generation": 1,
        "holder_ref": "agent:test:holder",
        "expires_at": "2026-08-11T00:00:00+00:00",
    }


def test_landed_plan_binds_expired_lease_generation() -> None:
    captured: dict[str, object] = {}
    lane = _lane()
    lane["lease_state"] = "expired"

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(Path, "is_dir", lambda _path: False)
        monkeypatch.setattr(
            linked_effect,
            "compile_observed_git_effect",
            lambda _root, _commitment, _effect, **kwargs: captured.update(kwargs) or object(),
        )

        linked_effect.linked_retirement_plan(
            Path("/control"),
            lane,
            accepted=("dev", "b" * 40),
            authority=lane,
            mode="landed",
            actor=ACTOR,
            worktree_clean=True,
        )

    assert captured["values"]["target_lease_state"] == "expired"
    assert captured["values"]["lease_generation_state"] == "expired"
    assert captured["values"]["lease_generation"] == {
        "lane_ref": "work/source",
        "generation": 1,
        "holder_ref": "agent:test:holder",
        "expires_at": "2026-08-11T00:00:00+00:00",
    }


def test_landed_plan_binds_missing_lease_without_inventing_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    lane = _lane()
    lane["lease_state"] = "missing"
    lane["lease"] = {"mints_authority": False}

    monkeypatch.setattr(Path, "is_dir", lambda _path: False)
    monkeypatch.setattr(
        linked_effect,
        "compile_observed_git_effect",
        lambda _root, _commitment, _effect, **kwargs: captured.update(kwargs) or object(),
    )

    linked_effect.linked_retirement_plan(
        Path("/control"),
        lane,
        accepted=("dev", "b" * 40),
        authority=lane,
        mode="landed",
        actor=ACTOR,
        worktree_clean=True,
    )

    assert captured["values"] == {
        "linked_worktree": {"path": "/lane", "clean": True},
        "target_lease_state": "missing",
    }


def test_landed_plan_binds_actor_subject_and_exact_git_facts(
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root)
    git(root, "add", ".ethos/profile.toml")
    git(root, "commit", "-m", "declare repository identity")
    head = git(root, "rev-parse", "HEAD")
    lane = _lane(path=(tmp_path / "lane").as_posix(), head=head)

    _root, plan = linked_effect.linked_retirement_plan(
        root,
        lane,
        accepted=("dev", head),
        authority=lane,
        mode="landed",
        actor=ACTOR,
        worktree_clean=True,
    )

    assert plan.request["subject"] == "work/source"
    assert plan.authority["actor"] == ACTOR
    assert plan.authority["subject"] == "work/source"
    for duplicated_coordinate in (
        "branch",
        "accepted_branch",
        "accepted_head",
        "authority_branch",
        "authority_head",
    ):
        assert duplicated_coordinate not in plan.policy
    assert plan.facts["values"]["refs"] == {"refs/heads/work/source": head}
    assert plan.facts["values"]["assertions"] == {"refs/heads/dev": head}
    assert plan.facts["values"]["linked_worktree"] == {
        "path": (tmp_path / "lane").as_posix(),
        "clean": True,
    }


def test_landed_plan_admits_the_exact_expired_lease_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root)
    git(root, "add", ".ethos/profile.toml")
    git(root, "commit", "-m", "declare repository identity")
    head = git(root, "rev-parse", "HEAD")
    git(root, "branch", "work/source", head)
    lease = strict_lease(
        branch="work/source",
        holder="agent:test:case:former-holder",
        expires_at=datetime.now(UTC) - timedelta(days=1),
    )
    record = acquire_lease(state_database(root), lease=lease)
    lane = _lane(path=(tmp_path / "lane").as_posix(), head=head)
    lane["lease_state"] = "expired"
    lane["lease"] = {
        "holder_ref": record["holder_ref"],
        "generation": record["generation"],
        "expires_at": record["expires_at"],
    }
    monkeypatch.setenv("ETHOS_ACTOR", ACTOR)

    _root, plan = linked_effect.linked_retirement_plan(
        root,
        lane,
        accepted=("dev", head),
        authority=lane,
        mode="landed",
        actor=ACTOR,
        worktree_clean=True,
    )

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


def test_effect_gaps_recheck_successor_checkout_and_archive_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane = _lane()
    lane["archive_absorption"] = {"change": "x"}
    authority = _lane(branch="work/authority", path="/authority", head="c" * 40)
    policy = BranchRolePolicy()
    monkeypatch.setattr(
        effects,
        "output",
        lambda _root, *args: policy.accepted_branch if args[0] == "symbolic-ref" else "b" * 40,
    )
    monkeypatch.setattr(Path, "resolve", lambda self: self)
    monkeypatch.setattr(effects, "actor_ref", lambda: "agent:test:holder")

    gaps = effects.effect_gaps(
        Path("/wrong"),
        Path("/control"),
        mode="superseded",
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )
    assert gaps == ["retirement_authority_checkout_stale"]

    monkeypatch.setattr(
        effects,
        "output",
        lambda root, *args: (
            policy.accepted_branch
            if root == Path("/control") and args[0] == "symbolic-ref"
            else "work/authority"
            if args[0] == "symbolic-ref"
            else "b" * 40
        ),
    )
    monkeypatch.setattr(effects, "reobservation_gaps", lambda *_args: [])
    monkeypatch.setattr(effects, "archived_carrier_absorption", lambda *_args, **_kwargs: {})
    gaps = effects.effect_gaps(
        Path("/authority"),
        Path("/control"),
        mode="superseded",
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )
    assert gaps == ["retirement_archive_absorption_stale"]


@pytest.mark.parametrize(
    ("returncode", "value", "gap"),
    [(1, "", "retirement_ref_unavailable"), (0, "other", "retirement_ref_stale")],
)
def test_reobservation_reports_unavailable_and_stale_native_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    value: str,
    gap: str,
) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()
    monkeypatch.setattr(
        effects,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, value, ""),
    )

    assert gap in effects.reobservation_gaps("work/source", lane.as_posix(), "a" * 40)


def test_superseded_retirement_retires_exact_unbound_lane_without_recreating_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(tmp_path, holder_ref=holder)
    install_fixture_hook_runtime(repo)
    git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    request = _retirement_request(head, accepted).model_copy(update={"path": lane.as_posix()})

    planned = retire_linked_work_lane(root=repo, mode="superseded", request=request)

    assert_public_decision(
        planned,
        verdict="pass",
        state="ready_to_retire_superseded",
        gaps=[],
    )
    assert planned["lane"]["recovery_required"] is True
    assert not lane.exists()

    applied = retire_linked_work_lane(
        root=repo,
        mode="superseded",
        request=request.model_copy(update={"apply": True}),
    )

    assert_public_decision(applied, verdict="pass", state="retired", gaps=[])
    assert "recovery" not in applied
    _assert_retired(repo, lane, database)


def test_superseded_retirement_keeps_unbound_lane_absent_when_ref_effect_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    holder = "agent:test:case:partial-recovery"
    repo, lane, head, accepted, database = superseded_work_lane(tmp_path, holder_ref=holder)
    install_fixture_hook_runtime(repo)
    git(repo, "worktree", "remove", lane.as_posix())
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    monkeypatch.setattr(
        "ethos.adapters.mutation.lane_retirement.operation.delete_operation_ref",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("git_effect_cas_rejected")),
    )
    request = _retirement_request(head, accepted, apply=True).model_copy(
        update={"path": lane.as_posix()}
    )

    report = retire_linked_work_lane(root=repo, mode="superseded", request=request)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["git_effect_cas_rejected"]
    assert not lane.exists()
    assert report["completed_effects"] == []
    assert report["remaining_effects"] == ["delete_ref", "revoke_lease"]
    assert "ethos lane retire recover" in report["next_action"]
    assert git(repo, "rev-parse", BRANCH) == head
    assert observe_lease(database, BRANCH).state == "valid"


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
    assert gap in report["required_gaps"]
    assert git(repo, "rev-parse", BRANCH) == head
    assert observe_lease(database, BRANCH).state == "valid"
