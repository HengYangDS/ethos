"""Fail-closed boundaries for native ownerless closeout admission."""

from __future__ import annotations

import hashlib
import stat
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.closeout.ownerless.admission.core as admission_api
import ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.core as admission
import ethos.adapters.mutation.resolution.closeout.ownerless.admission.facts.fence as admission_fence
import ethos.adapters.mutation.resolution.closeout.ownerless.workspace as policy
import ethos.adapters.mutation.resolution.observation as observation
import ethos.contracts.branch.roles as roles
import ethos.contracts.resolution.lane as lane

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_EXECUTOR = "agent:codex:thread:executor"


class _WorkLanePolicy:
    accepted_branch = "dev"

    def role_for_branch(self, _branch: str) -> str:
        return roles.ROLE_WORK_LANE


def _exact_observation(root: Path, *, head: str = "a" * 40) -> lane.LaneObservation:
    return lane.LaneObservation(
        lane_ref="work/ownerless",
        head=head,
        lane_incarnation_id="lane-incarnation:ownerless",
        path=(root / "checkout").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def _assert_admission_gap(call: Callable[[], object], gap: str, detail: str | None = None) -> None:
    with pytest.raises(admission_fence.OwnerlessCloseoutAdmissionError) as raised:
        call()
    assert raised.value.gap == gap
    if detail is not None:
        assert raised.value.detail == detail


def _assert_policy_gap(call: Callable[[], object], detail: str) -> None:
    with pytest.raises(observation.OwnerlessGitObservationError) as raised:
        call()
    assert (raised.value.kind, raised.value.detail) == ("unverifiable", detail)


def test_public_admission_translates_an_unclassified_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected(**_kwargs: object) -> object:
        raise RuntimeError

    monkeypatch.setattr(admission, "admit_ownerless_closeout_facts", unexpected)

    _assert_admission_gap(
        lambda: admission_api.admit_ownerless_closeout(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={},
            executor_ref=_EXECUTOR,
        ),
        "lane_resolution_ownerless_admission_unverifiable",
        "RuntimeError",
    )


def test_native_admission_maps_untyped_decision_snapshot_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        admission, "_authority_context", lambda *_args: (_WorkLanePolicy(), _EXECUTOR)
    )
    monkeypatch.setattr(admission, "current_record_root", lambda _root: tmp_path / "records")

    def invalid_snapshot(**_kwargs: object) -> object:
        raise RuntimeError

    monkeypatch.setattr(admission.validation, "admit_ownerless_decision_snapshot", invalid_snapshot)

    _assert_admission_gap(
        lambda: admission.admit_ownerless_closeout_facts(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={},
            executor_ref=_EXECUTOR,
        ),
        "lane_resolution_ownerless_decision_invalid",
        "records",
    )


def test_native_admission_reports_the_exact_stale_observation_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    admitted = _exact_observation(tmp_path)
    observed = _exact_observation(tmp_path, head="d" * 40)
    model = SimpleNamespace(observation=admitted)
    facts = SimpleNamespace(observation=observed)
    monkeypatch.setattr(
        admission, "_authority_context", lambda *_args: (_WorkLanePolicy(), _EXECUTOR)
    )
    monkeypatch.setattr(admission, "current_record_root", lambda _root: tmp_path / "records")
    monkeypatch.setattr(
        admission.validation,
        "admit_ownerless_decision_snapshot",
        lambda **_kwargs: (model, b"decision"),
    )
    monkeypatch.setattr(admission, "_git_observation", lambda *_args: facts)

    _assert_admission_gap(
        lambda: admission.admit_ownerless_closeout_facts(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={},
            executor_ref=_EXECUTOR,
        ),
        "lane_resolution_ownerless_observation_stale",
        "head",
    )


def test_native_admission_rejects_a_competing_fence_without_a_retry_reservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed = _exact_observation(tmp_path)
    model = SimpleNamespace(
        decision_id="lane-decision:00000000-0000-4000-8000-000000000111",
        observation=observed,
        chronicle_digest="d" * 64,
    )
    facts = SimpleNamespace(
        observation=observed,
        accepted_head="e" * 40,
        registration_token=object(),
    )
    monkeypatch.setattr(
        admission, "_authority_context", lambda *_args: (_WorkLanePolicy(), _EXECUTOR)
    )
    monkeypatch.setattr(admission, "current_record_root", lambda _root: tmp_path / "records")
    monkeypatch.setattr(
        admission.validation,
        "admit_ownerless_decision_snapshot",
        lambda **_kwargs: (model, b"decision"),
    )
    monkeypatch.setattr(admission, "_git_observation", lambda *_args: facts)
    monkeypatch.setattr(admission, "_chronicle", lambda *_args: None)
    monkeypatch.setattr(
        admission.receipt,
        "ownerless_reservation_admission_or_gap",
        lambda **_kwargs: (None, ""),
    )
    monkeypatch.setattr(admission, "_state", lambda *_args: ("present", None))

    _assert_admission_gap(
        lambda: admission.admit_ownerless_closeout_facts(
            root=tmp_path,
            decision_path=tmp_path / "decision.json",
            decision={},
            executor_ref=_EXECUTOR,
        ),
        "lane_resolution_ownerless_fence_mismatch",
        "competition",
    )


def test_authority_context_preserves_classified_errors_and_rejects_rewritten_executors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    classified = admission_fence.OwnerlessCloseoutAdmissionError("exact", "detail")
    monkeypatch.setattr(
        admission.workspace,
        "read_optional_root_bound_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(classified),
    )
    with pytest.raises(admission_fence.OwnerlessCloseoutAdmissionError) as raised:
        admission._authority_context(tmp_path, _EXECUTOR)  # noqa: SLF001, RUF100
    assert raised.value is classified

    monkeypatch.setattr(
        admission.workspace,
        "read_optional_root_bound_regular_file",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        admission,
        "HolderRef",
        SimpleNamespace(
            parse=lambda _value: SimpleNamespace(serialize=lambda: "agent:codex:thread:other")
        ),
    )
    _assert_admission_gap(
        lambda: admission._authority_context(tmp_path, _EXECUTOR),  # noqa: SLF001, RUF100
        "lane_resolution_ownerless_policy_invalid",
        "executor_ref",
    )


def test_chronicle_observation_rejects_unsafe_path_types_and_unverifiable_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unsafe = SimpleNamespace(chronicle_ref="not-a-chronicle", chronicle_digest="")
    _assert_admission_gap(
        lambda: admission._chronicle(tmp_path, unsafe, "a" * 40),  # noqa: SLF001, RUF100
        "lane_resolution_ownerless_chronicle_invalid",
        "path",
    )

    chronicle = "evidence/chronicle/ownerless.md"
    expected = SimpleNamespace(chronicle_ref=chronicle, chronicle_digest="d" * 64)
    monkeypatch.setattr(
        admission.git,
        "read_root_bound_regular_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            observation.OwnerlessGitObservationError("unverifiable", "path")
        ),
    )
    _assert_admission_gap(
        lambda: admission._chronicle(tmp_path, expected, "a" * 40),  # noqa: SLF001, RUF100
        "lane_resolution_ownerless_chronicle_invalid",
        "path_type",
    )

    raw = b"lane_resolution/retire\n"
    accepted = SimpleNamespace(
        chronicle_ref=chronicle,
        chronicle_digest=hashlib.sha256(raw).hexdigest(),
    )
    monkeypatch.setattr(
        admission.git,
        "read_root_bound_regular_file",
        lambda *_args, **_kwargs: SimpleNamespace(raw=raw),
    )
    monkeypatch.setattr(
        admission.git,
        "git_object_bytes",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            observation.OwnerlessGitObservationError("unverifiable", "object")
        ),
    )
    _assert_admission_gap(
        lambda: admission._chronicle(tmp_path, accepted, "a" * 40),  # noqa: SLF001, RUF100
        "lane_resolution_ownerless_git_unverifiable",
        "chronicle_git",
    )


@pytest.mark.parametrize(
    ("kind", "detail", "gap"),
    [
        ("dirty", "tracked", "lane_resolution_ownerless_worktree_dirty"),
        ("registration", "accepted_head", "lane_resolution_ownerless_accepted_head_stale"),
        ("registration", "target", "lane_resolution_ownerless_observation_stale"),
        ("unverifiable", "git", "lane_resolution_ownerless_git_unverifiable"),
    ],
)
def test_git_observation_translates_each_native_failure_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    detail: str,
    gap: str,
) -> None:
    monkeypatch.setattr(
        admission.git,
        "observe_ownerless_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            observation.OwnerlessGitObservationError(kind, detail)
        ),
    )

    _assert_admission_gap(
        lambda: admission._git_observation(tmp_path, "work/ownerless", "dev"),  # noqa: SLF001, RUF100
        gap,
        detail,
    )


def test_native_admission_maps_database_failure_and_keeps_equal_observation_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        admission,
        "state_database",
        lambda _root: (_ for _ in ()).throw(OSError("state unavailable")),
    )
    _assert_admission_gap(
        lambda: admission._database(tmp_path),  # noqa: SLF001, RUF100
        "lane_resolution_ownerless_state_unverifiable",
        "database",
    )

    exact = _exact_observation(tmp_path)
    assert admission._observation_difference(exact, exact) == "observation"  # noqa: SLF001, RUF100


def test_policy_reader_rejects_racing_absence_and_unreadable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = observation.DescriptorIdentity(1, 2, stat.S_IFDIR, 3, 4, 5)
    with monkeypatch.context() as scoped:
        scoped.setattr(policy.posix, "entry_directory_identity", lambda *_args: None)
        scoped.setattr(policy, "_entry_absent", lambda *_args, **_kwargs: False)
        _assert_policy_gap(
            lambda: policy._open_parent(tmp_path, 1, identity, [], (".ethos",)),  # noqa: SLF001, RUF100
            "root_bound_file",
        )

    with monkeypatch.context() as scoped:
        scoped.setattr(policy.posix, "entry_file_identity", lambda *_args: None)
        scoped.setattr(policy, "_entry_absent", lambda *_args, **_kwargs: False)
        _assert_policy_gap(
            lambda: policy._read_optional_file(  # noqa: SLF001, RUF100
                tmp_path, 1, identity, [], 1, "workspace.toml", 1024
            ),
            "root_bound_file",
        )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            policy.posix,
            "entry_file_identity",
            lambda *_args: (1, 2, stat.S_IFREG, 3, 4, 5),
        )
        scoped.setattr(policy.posix, "read_bound_file", lambda *_args, **_kwargs: None)
        _assert_policy_gap(
            lambda: policy._read_optional_file(  # noqa: SLF001, RUF100
                tmp_path, 1, identity, [], 1, "workspace.toml", 1024
            ),
            "root_bound_file",
        )


def test_policy_reader_detects_opened_chain_and_root_descriptor_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    held = observation.DescriptorIdentity(1, 2, stat.S_IFDIR, 3, 4, 5)
    replacement = observation.DescriptorIdentity(1, 3, stat.S_IFDIR, 3, 4, 5)
    with monkeypatch.context() as scoped:
        scoped.setattr(policy.os, "fstat", lambda _descriptor: object())
        scoped.setattr(policy, "_identity", lambda _metadata: replacement)
        _assert_policy_gap(
            lambda: policy._require_bound_chain(  # noqa: SLF001, RUF100
                tmp_path, 1, held, [(1, ".ethos", 2, held)]
            ),
            "root_bound_file",
        )

    with monkeypatch.context() as scoped:
        scoped.setattr(policy.os, "fstat", lambda _descriptor: object())
        scoped.setattr(policy, "_identity", lambda _metadata: held)
        scoped.setattr(policy.posix, "directory_descriptor_is_live", lambda *_args: False)
        _assert_policy_gap(
            lambda: policy._require_bound_chain(tmp_path, 1, held, []),  # noqa: SLF001, RUF100
            "root_bound_file",
        )


def test_policy_root_binding_closes_only_acquired_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = observation.DescriptorIdentity(1, 2, stat.S_IFDIR, 3, 4, 5)
    closed: list[int] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(policy.posix, "open_directory_path", lambda *_args, **_kwargs: 7)
        scoped.setattr(policy.os, "fstat", lambda _descriptor: object())
        scoped.setattr(policy, "_identity", lambda _metadata: identity)
        scoped.setattr(policy.posix, "directory_descriptor_is_live", lambda *_args: False)
        scoped.setattr(policy.os, "close", closed.append)
        _assert_policy_gap(
            lambda: policy._pin_root(tmp_path),  # noqa: SLF001, RUF100
            "root",
        )
    assert closed == [7]

    closed.clear()
    with monkeypatch.context() as scoped:
        scoped.setattr(policy.posix, "open_directory_path", lambda *_args, **_kwargs: 8)
        scoped.setattr(
            policy.os,
            "fstat",
            lambda _descriptor: (_ for _ in ()).throw(OSError("descriptor lost")),
        )
        scoped.setattr(policy.os, "close", closed.append)
        _assert_policy_gap(
            lambda: policy._pin_root(tmp_path),  # noqa: SLF001, RUF100
            "root",
        )
    assert closed == [8]

    closed.clear()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            policy.posix,
            "open_directory_path",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                observation.OwnerlessGitObservationError("unverifiable", "root")
            ),
        )
        scoped.setattr(policy.os, "close", closed.append)
        _assert_policy_gap(
            lambda: policy._pin_root(tmp_path),  # noqa: SLF001, RUF100
            "root",
        )
    assert closed == []

    with monkeypatch.context() as scoped:
        scoped.setattr(
            policy.posix,
            "open_directory_path",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("root unavailable")),
        )
        scoped.setattr(policy.os, "close", closed.append)
        _assert_policy_gap(
            lambda: policy._pin_root(tmp_path),  # noqa: SLF001, RUF100
            "root",
        )
    assert closed == []

    _assert_policy_gap(
        lambda: policy._relative_parts(7),  # noqa: SLF001, RUF100
        "path",
    )


def test_optional_policy_reader_maps_operational_root_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = observation.DescriptorIdentity(1, 2, stat.S_IFDIR, 3, 4, 5)
    monkeypatch.setattr(
        policy,
        "_pin_root",
        lambda _root: (tmp_path, 7, identity),
    )
    monkeypatch.setattr(
        policy,
        "_open_parent",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("root unavailable")),
    )
    monkeypatch.setattr(policy.os, "close", lambda _descriptor: None)

    _assert_policy_gap(
        lambda: policy.read_optional_root_bound_regular_file(
            tmp_path,
            ".ethos/workspace.toml",
            maximum_bytes=1024,
        ),
        "root_bound_file",
    )
