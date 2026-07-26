from __future__ import annotations

import hashlib
import inspect
import json
import os
import sqlite3
import subprocess
from copy import deepcopy
from dataclasses import FrozenInstanceError
from dataclasses import dataclass
from dataclasses import fields
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.mutation.resolution.closeout.ownerless.admission.core as native_admission_api
import ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.core as native_admission
import ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence as native_admission_fence
import ethos.adapters.mutation.resolution.closeout.ownerless.workspace as native_policy
import ethos.adapters.mutation.resolution.observation as resolution_observation
from ethos.adapters.mutation.resolution.records.core import canonical_current_record_bytes
from ethos.adapters.mutation.resolution.records.reservations import target_digest
from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.store.state.closeout import acquire_closeout_fence
from ethos.adapters.store.state.closeout import release_closeout_fence
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos_core.contracts.resolution.closeout import OwnerlessCloseoutReservation
from ethos_core.contracts.resolution.lane import LaneResolutionDecision

if TYPE_CHECKING:
    from pathlib import Path


_NATIVE_EXECUTOR = "agent:codex:thread:executor"
_NATIVE_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_NATIVE_CHRONICLE_REF = "evidence/chronicle/ownerless-closeout/2026-07-25.md"


@dataclass
class _NativeScenario:
    repo: Path
    target: Path
    branch: str
    accepted_head: str
    decision_path: Path
    decision: dict[str, Any]
    facts: resolution_observation.OwnerlessGitFacts


def _native_git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _native_commit(root: Path, message: str) -> str:
    _native_git(root, "add", "-A")
    _native_git(root, "-c", "commit.gpgsign=false", "commit", "-m", message)
    return _native_git(root, "rev-parse", "HEAD")


def _native_workspace_text(work_prefix: str = "work/") -> str:
    return (
        "[branch_roles]\n"
        'release_branch = "main"\n'
        'accepted_branch = "dev"\n'
        'candidate_branch = "candidate/dev"\n'
        f'work_branch_prefix = "{work_prefix}"\n'
        'submit_branch_prefix = "submit/"\n'
        'release_mirror = "independent"\n'
        "repository_family_worktrees = true\n"
    )


def _native_new_scenario(
    tmp_path: Path,
    *,
    work_prefix: str = "work/",
    branch: str | None = None,
    include_policy: bool = True,
) -> _NativeScenario:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _native_git(repo, "init", "-b", "dev")
    _native_git(repo, "config", "user.email", "tests@example.invalid")
    _native_git(repo, "config", "user.name", "ETHOS Tests")
    if include_policy:
        workspace = repo / ".ethos" / "workspace.toml"
        workspace.parent.mkdir()
        workspace.write_text(_native_workspace_text(work_prefix), encoding="utf-8")
    chronicle = repo / _NATIVE_CHRONICLE_REF
    chronicle.parent.mkdir(parents=True)
    chronicle.write_bytes(b"# Ownerless closeout\n\nlane_resolution/retire\n")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    base_head = _native_commit(repo, "base")
    lane_ref = branch or f"{work_prefix}ownerless"
    _native_git(repo, "branch", lane_ref, base_head)
    (repo / "accepted.txt").write_text("accepted\n", encoding="utf-8")
    accepted_head = _native_commit(repo, "accepted")
    target = tmp_path / "registered" / "arbitrary-checkout-name"
    target.parent.mkdir(parents=True)
    _native_git(repo, "worktree", "add", target.as_posix(), lane_ref)
    facts = resolution_observation.observe_ownerless_git(
        repo, branch=lane_ref, accepted_branch="dev"
    )
    decision = LaneResolutionDecision(
        decision_id=_NATIVE_DECISION_ID,
        disposition="retire",
        observation=facts.observation,
        evidence_refs=("evidence:review",),
        chronicle_ref=_NATIVE_CHRONICLE_REF,
        chronicle_digest=hashlib.sha256(chronicle.read_bytes()).hexdigest(),
        recovery_plan="Retire only after native admission and exact fencing.",
        reason="The exact clean ownerless target is absorbed by accepted history.",
        break_glass=True,
    ).to_payload()
    decision_path = current_record_root(repo) / "decisions" / "decision.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_bytes(canonical_current_record_bytes(decision))
    return _NativeScenario(repo, target, lane_ref, accepted_head, decision_path, decision, facts)


def _native_write_decision(scenario: _NativeScenario, payload: dict[str, Any]) -> None:
    scenario.decision = payload
    scenario.decision_path.write_bytes(canonical_current_record_bytes(payload))


def _native_update_chronicle_digest(scenario: _NativeScenario) -> None:
    changed = deepcopy(scenario.decision)
    raw = (scenario.repo / _NATIVE_CHRONICLE_REF).read_bytes()
    changed["chronicle_digest"] = hashlib.sha256(raw).hexdigest()
    _native_write_decision(scenario, changed)


def _native_admit(scenario: _NativeScenario, **overrides: Any) -> Any:
    values: dict[str, Any] = {
        "root": scenario.repo,
        "decision_path": scenario.decision_path,
        "decision": scenario.decision,
        "executor_ref": _NATIVE_EXECUTOR,
    }
    values.update(overrides)
    return native_admission_api.admit_ownerless_closeout(**values)


def _native_gap(call: Any, expected: str, detail: str | None = None) -> None:
    with pytest.raises(native_admission_fence.OwnerlessCloseoutAdmissionError) as raised:
        call()
    assert raised.value.gap == expected
    if detail is not None:
        assert raised.value.detail == detail


def _native_acquire_fence(scenario: _NativeScenario, admission: Any) -> dict[str, object]:
    return acquire_closeout_fence(
        state_database(scenario.repo),
        subject=admission.observation.lane_ref,
        expected_head=admission.observation.head,
        decision_id=admission.decision.decision_id,
        executor_ref=admission.executor_ref,
        accepted_branch=admission.accepted_branch,
        accepted_head=admission.accepted_head,
        target_path=admission.observation.path,
        lane_incarnation_id=admission.observation.lane_incarnation_id,
        observation_digest=admission.observation.digest(),
        decision_sha256=admission.decision_sha256,
        chronicle_digest=admission.decision.chronicle_digest,
    )


def _native_reservation(admission: Any, **changes: object) -> dict[str, object]:
    values: dict[str, object] = {
        "schema_version": 2,
        "decision_id": admission.decision.decision_id,
        "lane_ref": admission.observation.lane_ref,
        "head": admission.observation.head,
        "executor_ref": admission.executor_ref,
        "decision_sha256": admission.decision_sha256,
        "accepted_branch": admission.accepted_branch,
        "accepted_head": admission.accepted_head,
        "target_digest": admission.target_digest,
        "target_binding_digest": admission.target_binding_digest,
        "phase": "reserved",
        "recovery_state": "reserved_no_effect",
        "postcondition_digest": "",
    }
    values.update(changes)
    return OwnerlessCloseoutReservation.model_validate(values, strict=True).to_payload()


def _native_write_reservation(scenario: _NativeScenario, payload: dict[str, object]) -> Path:
    destination = (
        current_record_root(scenario.repo) / "reservations" / f"{payload['target_digest']}.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(canonical_current_record_bytes(payload))
    return destination


def test_native_admission_is_frozen_slots_only_fact_state(tmp_path: Path) -> None:
    scenario = _native_new_scenario(tmp_path, work_prefix="topic/")
    admission = _native_admit(scenario)

    assert tuple(field.name for field in fields(admission)) == (
        "root",
        "decision_path",
        "decision",
        "decision_bytes",
        "decision_sha256",
        "observation",
        "registration_token",
        "executor_ref",
        "policy",
        "accepted_branch",
        "accepted_head",
        "target_digest",
        "target_binding_digest",
        "existing_reservation",
    )
    assert tuple(inspect.signature(native_admission_api.admit_ownerless_closeout).parameters) == (
        "root",
        "decision_path",
        "decision",
        "executor_ref",
    )
    assert tuple(
        inspect.signature(native_admission_api.reobserve_ownerless_closeout_under_fence).parameters
    ) == ("admission", "fence")
    assert not hasattr(admission, "__dict__")
    assert not any(callable(getattr(admission, field.name)) for field in fields(admission))
    assert admission.decision.to_payload() == scenario.decision
    assert admission.decision_bytes == canonical_current_record_bytes(scenario.decision)
    assert admission.decision_sha256 == hashlib.sha256(admission.decision_bytes).hexdigest()
    assert admission.observation == scenario.facts.observation
    assert admission.registration_token == scenario.facts.registration_token
    assert admission.policy.work_branch_prefix == "topic/"
    assert admission.accepted_head == scenario.accepted_head
    assert admission.target_digest == target_digest(
        scenario.branch, scenario.facts.observation.head
    )
    assert admission.existing_reservation is None
    with pytest.raises(FrozenInstanceError):
        admission.accepted_head = "0" * 40


@pytest.mark.parametrize(
    ("mutation", "gap", "detail"),
    [
        ("dict", "lane_resolution_ownerless_decision_stale", "decision"),
        ("bytes", "lane_resolution_ownerless_decision_invalid", "canonical_bytes"),
        ("digest", "lane_resolution_ownerless_decision_invalid", "observation_digest"),
        ("disposition", "lane_resolution_ownerless_decision_invalid", "disposition"),
    ],
)
def test_native_decision_path_bytes_digest_and_model_are_exact(
    tmp_path: Path, mutation: str, gap: str, detail: str
) -> None:
    scenario = _native_new_scenario(tmp_path)
    overrides: dict[str, object] = {}
    if mutation == "dict":
        changed = deepcopy(scenario.decision)
        changed["reason"] = "different supplied dictionary"
        overrides["decision"] = changed
    elif mutation == "bytes":
        scenario.decision_path.write_text(json.dumps(scenario.decision), encoding="utf-8")
    elif mutation == "digest":
        changed = deepcopy(scenario.decision)
        changed["observation_digest"] = "0" * 64
        _native_write_decision(scenario, changed)
    else:
        changed = deepcopy(scenario.decision)
        changed["disposition"] = "preserve"
        _native_write_decision(scenario, changed)

    _native_gap(lambda: _native_admit(scenario, **overrides), gap, detail)


@pytest.mark.parametrize(
    ("mutation", "gap", "detail"),
    [
        ("working", "lane_resolution_ownerless_chronicle_stale", "working_digest"),
        ("accepted", "lane_resolution_ownerless_chronicle_stale", "accepted_bytes"),
        ("disposition", "lane_resolution_ownerless_chronicle_invalid", "disposition"),
        ("accepted_mode", "lane_resolution_ownerless_chronicle_invalid", "accepted_mode"),
    ],
)
def test_native_chronicle_requires_exact_bytes_regular_mode_and_retire_disposition(
    tmp_path: Path, mutation: str, gap: str, detail: str
) -> None:
    scenario = _native_new_scenario(tmp_path)
    chronicle = scenario.repo / _NATIVE_CHRONICLE_REF
    if mutation == "working":
        chronicle.write_bytes(b"# drift\n\nlane_resolution/retire\n")
    elif mutation == "accepted":
        chronicle.write_bytes(b"# working replacement\n\nlane_resolution/retire\n")
        _native_update_chronicle_digest(scenario)
    elif mutation == "disposition":
        chronicle.write_bytes(b"lane_resolution/retired\n")
        _native_commit(scenario.repo, "wrong disposition")
        _native_update_chronicle_digest(scenario)
    else:
        chronicle.unlink()
        chronicle.symlink_to("lane_resolution/retire")
        _native_commit(scenario.repo, "symlink chronicle")
        chronicle.unlink()
        chronicle.write_bytes(b"lane_resolution/retire")
        _native_update_chronicle_digest(scenario)

    _native_gap(lambda: _native_admit(scenario), gap, detail)


@pytest.mark.parametrize(
    "text",
    [
        "[branch_roles\n",
        "branch_roles = []\n",
        _native_workspace_text().replace('accepted_branch = "dev"', "accepted_branch = 7"),
        _native_workspace_text().replace('work_branch_prefix = "work/"\n', ""),
        _native_workspace_text().replace(
            "repository_family_worktrees = true", "repository_family_worktrees = 1"
        ),
        _native_workspace_text() + "unexpected = true\n",
    ],
)
def test_present_policy_is_strict_and_never_falls_back_to_defaults(
    tmp_path: Path, text: str
) -> None:
    scenario = _native_new_scenario(tmp_path)
    (scenario.repo / ".ethos" / "workspace.toml").write_text(text, encoding="utf-8")

    _native_gap(
        lambda: _native_admit(scenario),
        "lane_resolution_ownerless_policy_invalid",
    )


def test_present_policy_cannot_be_hidden_by_a_racing_existence_precheck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _native_new_scenario(tmp_path)
    (scenario.repo / ".ethos" / "workspace.toml").write_text("[branch_roles\n", encoding="utf-8")
    monkeypatch.setattr(os.path, "lexists", lambda _path: False)

    _native_gap(
        lambda: _native_admit(scenario),
        "lane_resolution_ownerless_policy_invalid",
        "workspace",
    )


def test_absent_policy_alone_uses_defaults(tmp_path: Path) -> None:
    scenario = _native_new_scenario(tmp_path, include_policy=False)
    admission = _native_admit(scenario)
    assert admission.policy.work_branch_prefix == "work/"
    assert admission.accepted_branch == "dev"


@pytest.mark.parametrize(
    ("setup", "relative_path", "maximum_bytes", "expected"),
    [
        ("missing_parent", ".ethos/workspace.toml", 1024, None),
        ("missing_file", ".ethos/workspace.toml", 1024, None),
        ("directory", ".ethos/workspace.toml", 1024, ("unverifiable", "root_bound_file")),
        ("invalid_limit", ".ethos/workspace.toml", -1, ("unverifiable", "root_bound_file")),
        ("unsafe_path", "../workspace.toml", 1024, ("unverifiable", "path")),
    ],
)
def test_root_bound_optional_policy_reader_is_fail_closed(
    tmp_path: Path,
    setup: str,
    relative_path: str,
    maximum_bytes: int,
    expected: tuple[str, str] | None,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    if setup != "missing_parent":
        (root / ".ethos").mkdir()
    if setup == "directory":
        (root / ".ethos" / "workspace.toml").mkdir()

    if expected is None:
        assert (
            native_policy.read_optional_root_bound_regular_file(
                root, relative_path, maximum_bytes=maximum_bytes
            )
            is None
        )
        return

    with pytest.raises(resolution_observation.OwnerlessGitObservationError) as raised:
        native_policy.read_optional_root_bound_regular_file(
            root, relative_path, maximum_bytes=maximum_bytes
        )
    assert (raised.value.kind, raised.value.detail) == expected


@pytest.mark.parametrize(
    ("observed", "expected", "supplied", "gap"),
    [
        (("unverifiable", None), {"binding": "exact"}, None, "fence_unverifiable"),
        (("absent", None), {"binding": "exact"}, None, "fence_mismatch"),
        (
            ("present", {"binding": "different"}),
            {"binding": "exact"},
            None,
            "fence_mismatch",
        ),
        (
            ("present", {"binding": "exact"}),
            {"binding": "exact"},
            {"binding": "supplied-drift"},
            "fence_mismatch",
        ),
    ],
)
def test_native_fence_helpers_require_one_exact_observation(
    observed: tuple[str, dict[str, object] | None],
    expected: dict[str, object],
    supplied: dict[str, object] | None,
    gap: str,
) -> None:
    _native_gap(
        lambda: native_admission._exact_fence(  # noqa: SLF001, RUF100
            observed, expected, "probe", supplied=supplied
        ),
        f"lane_resolution_ownerless_{gap}",
        "probe",
    )


@pytest.mark.parametrize(
    ("observed", "gap"),
    [
        (("unverifiable", None), "fence_unverifiable"),
        (("absent", None), "fence_mismatch"),
        (("present", {"payload": {}}), "fence_mismatch"),
        (("present", {"payload": {"acquisition_id": 7}}), "fence_mismatch"),
    ],
)
def test_native_fence_acquisition_id_is_canonical_text(
    observed: tuple[str, dict[str, object] | None], gap: str
) -> None:
    _native_gap(
        lambda: native_admission._acquisition_id(observed, "probe"),  # noqa: SLF001, RUF100
        f"lane_resolution_ownerless_{gap}",
        "probe",
    )


@pytest.mark.parametrize("executor", [" agent:codex:thread:executor", False])
def test_executor_must_already_be_canonical_text(tmp_path: Path, executor: object) -> None:
    scenario = _native_new_scenario(tmp_path)
    _native_gap(
        lambda: _native_admit(scenario, executor_ref=executor),
        "lane_resolution_ownerless_policy_invalid",
        "executor_ref",
    )


def test_configured_work_prefix_is_authoritative(tmp_path: Path) -> None:
    admitted = _native_new_scenario(tmp_path / "admitted", work_prefix="topic/")
    assert _native_admit(admitted).observation.lane_ref == "topic/ownerless"

    rejected = _native_new_scenario(
        tmp_path / "rejected", work_prefix="topic/", branch="work/ownerless"
    )
    _native_gap(
        lambda: _native_admit(rejected),
        "lane_resolution_ownerless_target_role_invalid",
        "role",
    )


@pytest.mark.parametrize(
    ("ancestry", "gap"),
    [
        ("diverged", "lane_resolution_ownerless_target_not_accepted_ancestor"),
        ("unverifiable", "lane_resolution_ownerless_ancestry_unverifiable"),
    ],
)
def test_accepted_ancestry_preserves_three_states(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ancestry: str,
    gap: str,
) -> None:
    scenario = _native_new_scenario(tmp_path)
    module = native_admission
    monkeypatch.setattr(
        module.git,
        "git_ancestry",
        lambda *_args, **_kwargs: ancestry,
    )
    _native_gap(lambda: _native_admit(scenario), gap, "ancestry")


@pytest.mark.parametrize("record_state", ["invalid", "conflict", "sidecar"])
def test_invalid_current_records_and_sidecars_block(tmp_path: Path, record_state: str) -> None:
    scenario = _native_new_scenario(tmp_path)
    root = current_record_root(scenario.repo)
    gap = "lane_resolution_current_record_invalid"
    if record_state == "invalid":
        path = root / "receipts" / "invalid.json"
        path.parent.mkdir()
        path.write_text("{}\n", encoding="utf-8")
    elif record_state == "sidecar":
        path = root / "receipts" / ".invalid.receipt-reservation"
        path.parent.mkdir()
        path.write_bytes(b"not-a-decision\n")
    else:
        changed = deepcopy(scenario.decision)
        changed["reason"] = "conflicting canonical decision"
        path = root / "decisions" / "duplicate.json"
        path.write_bytes(canonical_current_record_bytes(changed))
        gap = "lane_resolution_decision_record_conflict"
    _native_gap(lambda: _native_admit(scenario), gap)


def test_exact_zero_effect_retry_is_classified_in_existing_reservation(
    tmp_path: Path,
) -> None:
    scenario = _native_new_scenario(tmp_path)
    first = _native_admit(scenario)
    payload = _native_reservation(first)
    _native_write_reservation(scenario, payload)
    replay = _native_admit(scenario)
    assert replay.existing_reservation == OwnerlessCloseoutReservation.model_validate(
        payload, strict=True
    )


def test_zero_effect_retry_allows_only_descendant_accepted_head(
    tmp_path: Path,
) -> None:
    scenario = _native_new_scenario(tmp_path)
    first = _native_admit(scenario)
    payload = _native_reservation(first)
    _native_write_reservation(scenario, payload)
    (scenario.repo / "later.txt").write_text("later\n", encoding="utf-8")
    scenario.accepted_head = _native_commit(scenario.repo, "accepted descendant")
    replay = _native_admit(scenario)
    assert replay.accepted_head == scenario.accepted_head
    assert replay.existing_reservation == OwnerlessCloseoutReservation.model_validate(
        payload, strict=True
    )
    assert replay.target_binding_digest != payload["target_binding_digest"]


def test_retry_reservation_binding_must_match_observed_fence(tmp_path: Path) -> None:
    scenario = _native_new_scenario(tmp_path)
    admission = _native_admit(scenario)
    _native_acquire_fence(scenario, admission)
    competing = _native_reservation(admission, target_binding_digest="0" * 64)
    _native_write_reservation(scenario, competing)
    _native_gap(
        lambda: _native_admit(scenario),
        "lane_resolution_ownerless_reservation_competing",
        "reservation",
    )


def test_native_admission_distinguishes_current_lease_claim_and_expired_lease(
    tmp_path: Path,
) -> None:
    for index, claim_id in enumerate(("", "claim:bound")):
        scenario = _native_new_scenario(tmp_path / f"current-{index}")
        acquire_lease(
            state_database(scenario.repo),
            subject=scenario.branch,
            holder_ref="agent:test:case:holder",
            payload={"claim_id": claim_id},
        )
        _native_gap(
            lambda scenario=scenario: _native_admit(scenario),
            "lane_resolution_ownerless_coordinated",
            "claim" if claim_id else "lease",
        )

    expired = _native_new_scenario(tmp_path / "expired")
    acquire_lease(
        state_database(expired.repo),
        subject=expired.branch,
        holder_ref="agent:test:case:expired",
        ttl_seconds=-1,
        payload={"claim_id": "claim:expired"},
    )
    assert _native_admit(expired).existing_reservation is None


def test_native_admission_and_fenced_reobservation_ignore_unrelated_legacy_lease(
    tmp_path: Path,
) -> None:
    scenario = _native_new_scenario(tmp_path)
    db_path = state_database(scenario.repo)
    unrelated = f"{scenario.branch}-successor"
    acquire_lease(
        db_path,
        subject=unrelated,
        holder_ref="agent:test:case:unrelated-legacy",
        ttl_seconds=-1,
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps({"branch": unrelated, "path": "/tmp/legacy"}), unrelated),
        )

    admission = _native_admit(scenario)
    fence = _native_acquire_fence(scenario, admission)

    assert (
        native_admission_api.reobserve_ownerless_closeout_under_fence(
            admission=admission, fence=fence
        )
        == admission
    )


def test_fenced_reobservation_rejects_malformed_exact_subject_lease(tmp_path: Path) -> None:
    scenario = _native_new_scenario(tmp_path)
    db_path = state_database(scenario.repo)
    acquire_lease(
        db_path,
        subject=scenario.branch,
        holder_ref="agent:test:case:malformed-exact",
        ttl_seconds=-1,
    )
    admission = _native_admit(scenario)
    fence = _native_acquire_fence(scenario, admission)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (
                json.dumps({"branch": scenario.branch, "path": "/tmp/legacy"}),
                scenario.branch,
            ),
        )

    _native_gap(
        lambda: native_admission_api.reobserve_ownerless_closeout_under_fence(
            admission=admission, fence=fence
        ),
        "lane_resolution_ownerless_state_unverifiable",
        "lease",
    )


def test_fence_held_reobservation_returns_the_same_fact_snapshot(tmp_path: Path) -> None:
    scenario = _native_new_scenario(tmp_path)
    admission = _native_admit(scenario)
    fence = _native_acquire_fence(scenario, admission)
    observed = native_admission_api.reobserve_ownerless_closeout_under_fence(
        admission=admission, fence=fence
    )
    assert observed == admission


def test_fence_reobservation_allows_exact_retry_reservation_reset(tmp_path: Path) -> None:
    scenario = _native_new_scenario(tmp_path)
    initial = _native_admit(scenario)
    old_fence = _native_acquire_fence(scenario, initial)
    reservation_path = _native_write_reservation(
        scenario,
        _native_reservation(initial, target_binding_digest=old_fence["target_binding_digest"]),
    )
    retry = _native_admit(scenario)
    reservation_path.unlink()
    _native_gap(
        lambda: native_admission_api.reobserve_ownerless_closeout_under_fence(
            admission=retry, fence=old_fence
        ),
        "lane_resolution_ownerless_reobservation_stale",
        "existing_reservation",
    )
    release_closeout_fence(
        state_database(scenario.repo),
        subject=retry.observation.lane_ref,
        decision_id=retry.decision.decision_id,
        target_binding_digest=str(old_fence["target_binding_digest"]),
    )
    reset = replace(retry, existing_reservation=None)
    fresh_fence = _native_acquire_fence(scenario, reset)

    observed = native_admission_api.reobserve_ownerless_closeout_under_fence(
        admission=reset, fence=fresh_fence
    )

    assert observed == reset


def test_registration_token_drift_blocks_even_when_observation_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _native_new_scenario(tmp_path)
    admission = _native_admit(scenario)
    fence = _native_acquire_fence(scenario, admission)
    module = native_admission
    drifted = replace(
        admission.registration_token,
        administration_path=f"{admission.registration_token.administration_path}-drift",
    )
    monkeypatch.setattr(
        module.git,
        "observe_ownerless_git",
        lambda *_args, **_kwargs: resolution_observation.OwnerlessGitFacts(
            admission.accepted_head, admission.observation, drifted
        ),
    )
    _native_gap(
        lambda: native_admission_api.reobserve_ownerless_closeout_under_fence(
            admission=admission, fence=fence
        ),
        "lane_resolution_ownerless_reobservation_stale",
        "registration_token",
    )


@pytest.mark.parametrize("error_kind", ["classified", "unexpected", "base"])
def test_after_fence_probe_runs_from_finally_for_every_exception_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_kind: str,
) -> None:
    scenario = _native_new_scenario(tmp_path)
    admission = _native_admit(scenario)
    fence = _native_acquire_fence(scenario, admission)
    module = native_admission
    real_probe = module.state_closeout.probe_closeout_fence
    probes: list[str] = []
    expected = (
        "lane_resolution_ownerless_decision_stale"
        if error_kind == "classified"
        else "lane_resolution_ownerless_admission_unverifiable"
    )

    def probe(*args: Any, **kwargs: Any) -> tuple[str, dict[str, object] | None]:
        probes.append("probe")
        return real_probe(*args, **kwargs)

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        if error_kind == "classified":
            raise native_admission_fence.OwnerlessCloseoutAdmissionError(expected, "decision")
        if error_kind == "unexpected":
            raise RuntimeError(error_kind)
        raise KeyboardInterrupt

    monkeypatch.setattr(module.state_closeout, "probe_closeout_fence", probe)
    monkeypatch.setattr(module, "admit_ownerless_closeout_facts", fail)
    if error_kind == "base":
        with pytest.raises(KeyboardInterrupt):
            native_admission_api.reobserve_ownerless_closeout_under_fence(
                admission=admission, fence=fence
            )
    else:
        _native_gap(
            lambda: native_admission_api.reobserve_ownerless_closeout_under_fence(
                admission=admission, fence=fence
            ),
            expected,
        )
    assert probes == ["probe", "probe"]


def test_after_fence_mismatch_overrides_a_pending_reobservation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = _native_new_scenario(tmp_path)
    admission = _native_admit(scenario)
    fence = _native_acquire_fence(scenario, admission)
    module = native_admission
    real_probe = module.state_closeout.probe_closeout_fence
    calls = 0

    def probe(*args: Any, **kwargs: Any) -> tuple[str, dict[str, object] | None]:
        nonlocal calls
        calls += 1
        return real_probe(*args, **kwargs) if calls == 1 else ("absent", None)

    def fail(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(module.__name__)

    monkeypatch.setattr(module.state_closeout, "probe_closeout_fence", probe)
    monkeypatch.setattr(module, "admit_ownerless_closeout_facts", fail)
    _native_gap(
        lambda: native_admission_api.reobserve_ownerless_closeout_under_fence(
            admission=admission, fence=fence
        ),
        "lane_resolution_ownerless_fence_mismatch",
        "after",
    )
    assert calls == 2
