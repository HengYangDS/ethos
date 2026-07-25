from __future__ import annotations

import hashlib
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution._effects as closeout_git
import ethos.adapters.mutation.resolution.closeout.admission as closeout_admission
import ethos.adapters.mutation.resolution.closeout.effect as effect
import ethos.adapters.mutation.resolution.closeout.receipt as closeout_receipt
import ethos.adapters.mutation.resolution.records.reservations as reservations
from ethos.adapters.mutation.resolution.observation import observe_ownerless_git
from ethos.adapters.mutation.resolution.records.core import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.core import receipt_path
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import get_closeout_fence
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.resolution.lane import LaneResolutionDecision
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path

_EXECUTOR = "agent:codex:thread:executor"
_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"


@dataclass
class _Scenario:
    repo: Path
    target: Path
    decision_path: Path
    decision: dict[str, object]
    head: str
    accepted_head: str


def _scenario(tmp_path: Path) -> _Scenario:
    repo = init_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "dev")
    git(repo, "branch", "work/orphan", head)
    chronicle_ref = "evidence/chronicle/effect/retire.md"
    chronicle = repo / chronicle_ref
    chronicle.parent.mkdir(parents=True)
    chronicle.write_bytes(b"# Ownerless effect\n\nlane_resolution/retire\n")
    git(repo, "add", chronicle_ref)
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "record ownerless effect decision",
    )
    accepted_head = git(repo, "rev-parse", "dev")
    target = tmp_path / "registered" / "orphan"
    target.parent.mkdir()
    git(repo, "worktree", "add", target.as_posix(), "work/orphan")
    facts = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")
    decision = LaneResolutionDecision(
        decision_id=_DECISION_ID,
        disposition="retire",
        observation=facts.observation,
        evidence_refs=("evidence:effect",),
        chronicle_ref=chronicle_ref,
        chronicle_digest=hashlib.sha256(chronicle.read_bytes()).hexdigest(),
        recovery_plan="Reconcile the exact durable closeout binding.",
        reason="The clean ownerless lane is absorbed by accepted history.",
        break_glass=True,
    ).to_payload()
    decision_path = current_record_root(repo) / "decisions" / "effect.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_bytes(canonical_current_record_bytes(decision))
    return _Scenario(repo, target, decision_path, decision, head, accepted_head)


def _apply(scenario: _Scenario) -> dict[str, object]:
    return effect.retire_clean_ownerless_lane(
        root=scenario.repo,
        decision_path=scenario.decision_path,
        decision=scenario.decision,
        executor_ref=_EXECUTOR,
    )


def _reservation(scenario: _Scenario) -> dict[str, object]:
    path = _reservation_path(scenario)
    return reservations.read_ownerless_closeout_reservation(
        record_root=current_record_root(scenario.repo),
        path=path,
    )


def _reservation_path(scenario: _Scenario) -> Path:
    target = reservations.target_digest("work/orphan", scenario.head)
    return reservations.ownerless_closeout_reservation_path(scenario.repo, target)


@pytest.mark.parametrize(
    ("responses", "expected"),
    [
        ([subprocess.CompletedProcess([], 1, "", "")], ("absent", "")),
        ([subprocess.CompletedProcess([], 128, "", "fatal")], ("unverifiable", "")),
        ([OSError("probe failed")], ("unverifiable", "")),
        (
            [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, f"{'a' * 40}\n", ""),
            ],
            ("oid", "a" * 40),
        ),
    ],
)
def test_ownerless_ref_probe_has_explicit_three_state_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    responses: list[object],
    expected: tuple[str, str],
) -> None:
    queue = list(responses)

    def probe(*_args: object, **_kwargs: object):
        response = queue.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(closeout_git, "run_git", probe)
    assert closeout_git.probe_ownerless_ref(tmp_path, "work/orphan") == expected


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            subprocess.CompletedProcess([], 0, "worktree /other\nworktree /target\n", ""),
            "present",
        ),
        (subprocess.CompletedProcess([], 0, "worktree /other\n", ""), "absent"),
        (subprocess.CompletedProcess([], 128, "", "fatal"), "unverifiable"),
        (OSError("registration probe failed"), "unverifiable"),
        (subprocess.SubprocessError("registration probe failed"), "unverifiable"),
    ],
)
def test_ownerless_registration_probe_has_explicit_three_state_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    response: object,
    expected: str,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def run(_root: Path, *args: str, **kwargs: object):
        calls.append((args, kwargs))
        if isinstance(response, BaseException):
            raise response
        return response

    monkeypatch.setattr(closeout_git, "run_git", run)

    assert closeout_git.probe_ownerless_worktree_registration(tmp_path, "/target") == expected
    assert calls == [(("worktree", "list", "--porcelain"), {"check": False})]


def test_fresh_fence_acquisition_failure_blocks_before_reservation_or_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    events: list[str] = []

    def fail_fence(*_args: object, **_kwargs: object) -> dict[str, object]:
        events.append("fence")
        message = "state database unavailable"
        raise OSError(message)

    monkeypatch.setattr(effect, "acquire_closeout_fence", fail_fence)
    monkeypatch.setattr(
        effect,
        "reserve_ownerless_closeout_target",
        lambda **_kwargs: events.append("reservation"),
    )
    monkeypatch.setattr(
        effect,
        "retire_clean_ownerless_cas",
        lambda **_kwargs: events.append("effect"),
    )

    with pytest.raises(
        effect.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_fence_failed",
    ) as raised:
        _apply(scenario)

    assert str(raised.value) == "lane_resolution_ownerless_fence_failed"
    assert raised.value.reservation_visible is False
    assert events == ["fence"]
    assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") is None
    assert not _reservation_path(scenario).exists()
    assert scenario.target.is_dir()
    assert closeout_git.probe_ownerless_ref(scenario.repo, "work/orphan") == (
        "oid",
        scenario.head,
    )


def test_initial_reservation_failure_rolls_back_exact_fence_before_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    acquired: list[dict[str, object]] = []
    releases: list[dict[str, object]] = []
    effect_called = False
    real_acquire = effect.acquire_closeout_fence
    real_release = effect.release_closeout_fence

    def fail_reservation(**_kwargs: object) -> None:
        message = "reservation unavailable"
        raise OSError(message)

    def acquire(database: Path, **kwargs: object) -> dict[str, object]:
        fence = real_acquire(database, **kwargs)
        acquired.append(fence)
        return fence

    def release(database: Path, **kwargs: object) -> None:
        releases.append(kwargs)
        real_release(database, **kwargs)

    def retire(**_kwargs: object) -> None:
        nonlocal effect_called
        effect_called = True

    monkeypatch.setattr(effect, "acquire_closeout_fence", acquire)
    monkeypatch.setattr(effect, "reserve_ownerless_closeout_target", fail_reservation)
    monkeypatch.setattr(effect, "release_closeout_fence", release)
    monkeypatch.setattr(effect, "retire_clean_ownerless_cas", retire)

    with pytest.raises(
        effect.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_reservation_failed",
    ) as raised:
        _apply(scenario)

    assert str(raised.value) == "lane_resolution_ownerless_reservation_failed"
    assert raised.value.reservation_visible is False
    assert effect_called is False
    assert len(acquired) == 1
    assert len(releases) == 1
    assert releases[0]["subject"] == "work/orphan"
    assert releases[0]["decision_id"] == _DECISION_ID
    assert releases[0]["target_binding_digest"] == acquired[0]["target_binding_digest"]
    assert get_closeout_fence(state_database(scenario.repo), subject="work/orphan") is None
    assert not _reservation_path(scenario).exists()
    assert scenario.target.is_dir()
    assert closeout_git.probe_ownerless_ref(scenario.repo, "work/orphan") == (
        "oid",
        scenario.head,
    )


def test_final_reservation_transition_failure_retains_recovery_visibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    effects = 0
    real_retire = effect.retire_clean_ownerless_cas

    def retire(**kwargs: object) -> None:
        nonlocal effects
        effects += 1
        real_retire(**kwargs)

    def fail_transition(**_kwargs: object) -> None:
        message = "reservation transition unavailable"
        raise OSError(message)

    def unexpected_cleanup(*_args: object, **_kwargs: object) -> None:
        pytest.fail("post-effect transition failure must not release the fence")

    monkeypatch.setattr(effect, "retire_clean_ownerless_cas", retire)
    monkeypatch.setattr(effect, "transition_ownerless_closeout_reservation", fail_transition)
    monkeypatch.setattr(effect, "release_closeout_fence", unexpected_cleanup)

    with pytest.raises(
        effect.OwnerlessCloseoutError,
        match="lane_resolution_ownerless_reservation_update_failed",
    ) as raised:
        _apply(scenario)

    assert str(raised.value) == "lane_resolution_ownerless_reservation_update_failed"
    assert effects == 1
    assert (raised.value.phase, raised.value.recovery_state) == (
        "unknown",
        "transition_unknown",
    )
    assert raised.value.reservation_visible is True
    reservation = _reservation(scenario)
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "reserved",
        "reserved_no_effect",
    )
    fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    assert fence is not None
    assert reservation["target_binding_digest"] == fence["target_binding_digest"]
    assert not scenario.target.exists()
    assert closeout_git.probe_ownerless_ref(scenario.repo, "work/orphan") == ("absent", "")


def test_native_effect_uses_fresh_fence_digest_and_reaches_receipt_boundary(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path)
    binding = _apply(scenario)
    fence = get_closeout_fence(state_database(scenario.repo), subject="work/orphan")
    reservation = _reservation(scenario)

    assert fence is not None
    assert binding["target_binding_digest"] == fence["target_binding_digest"]
    assert reservation["target_binding_digest"] == fence["target_binding_digest"]
    assert reservation["phase"] == "receipt"
    assert reservation["recovery_state"] == "effect_complete_receipt_missing"
    assert not scenario.target.exists()
    assert closeout_git.probe_ownerless_ref(scenario.repo, "work/orphan") == ("absent", "")


@pytest.mark.parametrize("mutation", ["replacement_identity", "extra_sidecar"])
def test_fence_reobservation_rejects_receipt_reservation_drift(
    tmp_path: Path, mutation: str
) -> None:
    scenario = _scenario(tmp_path)
    admission = closeout_admission.admit_ownerless_closeout(
        root=scenario.repo,
        decision_path=scenario.decision_path,
        decision=scenario.decision,
        executor_ref=_EXECUTOR,
    )
    record_root = current_record_root(scenario.repo)
    with ExitStack() as stack:
        claimed, descriptor, gap = closeout_receipt.claim_receipt_reservation(
            stack,
            scenario.repo,
            record_root,
            _DECISION_ID,
            mode="create",
        )
        assert claimed is True
        assert descriptor is not None
        assert gap == ""
        binder = getattr(closeout_receipt, "bind_ownerless_receipt_reservation", None)
        assert binder is not None
        admission = binder(
            admission=admission,
            control_root=scenario.repo,
            artifact_root=record_root,
            descriptor=descriptor,
        )
        database = state_database(scenario.repo)
        fence = effect._acquire_fresh_fence(admission, database)  # noqa: SLF001, RUF100
        token = admission.receipt_reservation_token
        assert token is not None
        if mutation == "replacement_identity":
            token.path.unlink()
            token.path.write_bytes(token.raw)
        else:
            competitor_id = "lane-decision:00000000-0000-4000-8000-000000000002"
            competitor_receipt = receipt_path(
                scenario.repo,
                competitor_id,
                artifact_root=record_root,
            )
            competitor_receipt.with_name(
                f".{competitor_receipt.stem}.receipt-reservation"
            ).write_bytes(f"{competitor_id}\n".encode())
        try:
            with pytest.raises(closeout_admission.OwnerlessCloseoutAdmissionError) as raised:
                closeout_admission.reobserve_ownerless_closeout_under_fence(
                    admission=admission,
                    fence=fence,
                )
            assert raised.value.gap == "lane_resolution_ownerless_reservation_competing"
        finally:
            effect._release_unreserved_fence(admission, database, fence)  # noqa: SLF001, RUF100


def test_failed_remove_with_zero_effect_keeps_retry_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    real_run = closeout_git.run_git

    def fail_remove(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 1, "", "failed")
        return real_run(root, *args, **kwargs)

    monkeypatch.setattr(closeout_git, "run_git", fail_remove)
    with pytest.raises(effect.OwnerlessCloseoutError) as raised:
        _apply(scenario)
    assert str(raised.value) == "lane_resolution_ownerless_worktree_remove_failed"
    assert (raised.value.phase, raised.value.recovery_state) == (
        "reserved",
        "reserved_no_effect",
    )
    assert _reservation(scenario)["recovery_state"] == "reserved_no_effect"
    assert scenario.target.is_dir()


def test_failed_remove_after_real_removal_records_effect_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    real_run = closeout_git.run_git

    def remove_then_fail(root: Path, *args: str, **kwargs: object):
        if args[:2] == ("worktree", "remove"):
            completed = real_run(root, *args, **kwargs)
            assert completed.returncode == 0
            return subprocess.CompletedProcess(args, 1, "", "late failure")
        return real_run(root, *args, **kwargs)

    monkeypatch.setattr(closeout_git, "run_git", remove_then_fail)
    with pytest.raises(effect.OwnerlessCloseoutError, match="worktree_removed_ref_present"):
        _apply(scenario)
    reservation = _reservation(scenario)
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "effect",
        "worktree_removed_ref_present",
    )


def test_accepted_drift_after_reobservation_preserves_partial_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    real_reobserve = effect.reobserve_ownerless_closeout_under_fence

    def reobserve_then_drift(**kwargs: object):
        admission = real_reobserve(**kwargs)
        (scenario.repo / "late.txt").write_text("late\n", encoding="utf-8")
        git(scenario.repo, "add", "late.txt")
        git(
            scenario.repo,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "late accepted drift",
        )
        return admission

    monkeypatch.setattr(effect, "reobserve_ownerless_closeout_under_fence", reobserve_then_drift)
    with pytest.raises(effect.OwnerlessCloseoutError, match="accepted_head_stale") as raised:
        _apply(scenario)
    assert raised.value.recovery_state == "worktree_removed_ref_present"
    assert _reservation(scenario)["recovery_state"] == "worktree_removed_ref_present"


def test_post_cas_exception_records_transition_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    monkeypatch.setattr(
        effect,
        "verify_ownerless_postconditions",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("after cas")),
    )
    with pytest.raises(effect.OwnerlessCloseoutError, match="transition_unknown"):
        _apply(scenario)
    reservation = _reservation(scenario)
    assert (reservation["phase"], reservation["recovery_state"]) == (
        "unknown",
        "transition_unknown",
    )


def test_dangling_path_blocks_postconditions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    scenario = _scenario(tmp_path)
    real_cas = effect.retire_clean_ownerless_cas

    def cas_then_dangling(**kwargs: object) -> None:
        real_cas(**kwargs)
        scenario.target.symlink_to(tmp_path / "missing", target_is_directory=True)

    monkeypatch.setattr(effect, "retire_clean_ownerless_cas", cas_then_dangling)
    with pytest.raises(effect.OwnerlessCloseoutError, match="target_path_absent"):
        _apply(scenario)
    assert scenario.target.is_symlink()
    assert _reservation(scenario)["recovery_state"] == "postcondition_failed"
