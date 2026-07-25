from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution._effects as effect
from ethos_core.contracts.resolution.lane import LaneObservation

if TYPE_CHECKING:
    from pathlib import Path


def _observation(tmp_path: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/orphan",
        head="a" * 40,
        lane_incarnation_id="lane:cas",
        path=(tmp_path / "orphan").as_posix(),
        dirty=False,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def test_ownerless_cas_binds_accepted_noop_and_target_delete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def run(_root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0, "start: ok\nprepare: ok\ncommit: ok\n", "")

    monkeypatch.setattr(effect, "run_git", run)
    monkeypatch.setattr(
        effect,
        "probe_ownerless_ref",
        lambda _root, branch: ("oid", "d" * 40) if branch == "dev" else ("absent", ""),
    )
    effect.retire_clean_ownerless_cas(
        root=tmp_path,
        observation=observation,
        accepted_branch="dev",
        accepted_head="d" * 40,
    )
    stdin = str(calls[-1][1]["stdin"])
    assert f"update refs/heads/dev {'d' * 40} {'d' * 40}" in stdin
    assert f"delete refs/heads/work/orphan {'a' * 40}" in stdin
    assert calls[0][0] == ("worktree", "remove", observation.path)


def test_ownerless_cas_failure_after_removal_is_partial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)

    def run(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("worktree", "remove"):
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 1, "start: ok\n", "failed")

    monkeypatch.setattr(effect, "run_git", run)
    monkeypatch.setattr(
        effect,
        "probe_ownerless_ref",
        lambda _root, branch: ("oid", "d" * 40) if branch == "dev" else ("oid", observation.head),
    )
    monkeypatch.setattr(effect, "probe_ownerless_worktree_registration", lambda *_a: "absent")
    monkeypatch.setattr(effect, "probe_ownerless_path", lambda *_a: "absent")
    with pytest.raises(effect.OwnerlessCloseoutError) as raised:
        effect.retire_clean_ownerless_cas(
            root=tmp_path,
            observation=observation,
            accepted_branch="dev",
            accepted_head="d" * 40,
        )
    assert (raised.value.phase, raised.value.recovery_state) == (
        "effect",
        "worktree_removed_ref_present",
    )


def test_ownerless_remove_failure_with_unverifiable_probe_is_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    observation = _observation(tmp_path)
    monkeypatch.setattr(
        effect,
        "run_git",
        lambda *_a, **_k: subprocess.CompletedProcess([], 1, "", "failed"),
    )
    monkeypatch.setattr(effect, "probe_ownerless_ref", lambda *_a: ("unverifiable", ""))
    monkeypatch.setattr(effect, "probe_ownerless_worktree_registration", lambda *_a: "unverifiable")
    monkeypatch.setattr(effect, "probe_ownerless_path", lambda *_a: "present")
    with pytest.raises(effect.OwnerlessCloseoutError) as raised:
        effect.retire_clean_ownerless_cas(
            root=tmp_path,
            observation=observation,
            accepted_branch="dev",
            accepted_head="d" * 40,
        )
    assert (raised.value.phase, raised.value.recovery_state) == (
        "unknown",
        "transition_unknown",
    )
