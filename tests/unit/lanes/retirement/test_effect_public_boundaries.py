from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.contracts.branch.roles import BranchRolePolicy


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
            "lease_id": "lease:test",
            "epoch": 1,
            "holder_ref": holder,
            "expires_at": "2026-08-11T00:00:00+00:00",
            "payload_sha256": "b" * 64,
        },
    }


@pytest.mark.parametrize(
    ("error", "terminal", "expected"),
    [
        (OSError("uncertain"), True, {"observed": {"terminal": True}}),
        (
            sqlite3.OperationalError("uncertain"),
            False,
            {
                "verdict": "block",
                "state": "blocked",
                "required_gaps": ["lease_cleanup_failed"],
                "stderr": "uncertain",
                "observed": {"terminal": False},
            },
        ),
        (None, True, {"observed": {"terminal": True}}),
        (
            None,
            False,
            {
                "verdict": "block",
                "state": "blocked",
                "required_gaps": ["retirement_postcondition_not_terminal"],
                "observed": {"terminal": False},
            },
        ),
    ],
)
def test_retirement_result_distinguishes_uncertain_success_from_failure(
    monkeypatch: pytest.MonkeyPatch,
    error: OSError | sqlite3.Error | None,
    terminal: int,
    expected: dict[str, object],
) -> None:
    observed = {"terminal": bool(terminal)}
    monkeypatch.setattr(effects, "retirement_observation", lambda *_args: observed)
    monkeypatch.setattr(effects, "retirement_terminal", lambda _observed: bool(terminal))

    assert (
        effects.retirement_result(Path("/repo"), Path("/control"), _lane(), result={}, error=error)
        == expected
    )


@pytest.mark.parametrize(
    ("accepted_state", "authority_state", "source_state", "restored", "gaps"),
    [
        (
            "expected",
            "moved",
            "moved",
            False,
            {
                "authority_ref_changed_after_worktree_removed",
                "retirement_ref_moved_after_worktree_removed",
            },
        ),
        (
            "expected",
            "unavailable",
            "absent",
            False,
            {
                "authority_ref_state_unavailable_after_worktree_removed",
                "retirement_ref_absent_after_failed_delete",
            },
        ),
        (
            "expected",
            "expected",
            "expected",
            False,
            {"worktree_restore_failed_after_ref_transition"},
        ),
    ],
)
def test_failed_ref_transition_reports_each_preservation_failure(
    monkeypatch: pytest.MonkeyPatch,
    accepted_state: str,
    authority_state: str,
    source_state: str,
    restored: int,
    gaps: set[str],
) -> None:
    def outcome(_root: Path, branch: str, _head: str) -> str:
        return {
            "dev": accepted_state,
            "work/authority": authority_state,
            "work/source": source_state,
        }[branch]

    monkeypatch.setattr(effects, "ref_outcome", outcome)
    monkeypatch.setattr(
        effects,
        "restore_worktree",
        lambda *_args: {"state": "recognized" if restored else "blocked"},
    )

    report = effects.failed_ref_transition(
        Path("/control"),
        lane=_lane(),
        target=("work/source", "a" * 40),
        accepted=("dev", "b" * 40),
        authority=("work/authority", "c" * 40),
        stderr="effect rejected",
    )

    assert gaps <= set(report["required_gaps"])
    assert report["ref_state"] == source_state
    assert report["ref_preserved"] is (source_state == "expected")


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
    ("carrier", "ancestor", "paths", "archives", "blobs", "expected"),
    [
        ("README.md", True, (), (), {}, {}),
        ("openspec/changes/x/commitment.toml", False, (), (), {}, {}),
        ("openspec/changes/x/commitment.toml", True, ("src/x.py",), ("archive/x",), {}, {}),
        (
            "openspec/changes/x/commitment.toml",
            True,
            ("openspec/changes/x/commitment.toml",),
            (),
            {},
            {},
        ),
        (
            "openspec/changes/x/commitment.toml",
            True,
            ("openspec/changes/x/commitment.toml",),
            ("openspec/changes/archive/2026-08-10-x",),
            {"source": "blob-a", "target": "blob-b"},
            {},
        ),
    ],
)
def test_archive_absorption_rejects_ambiguous_or_nonidentical_carriers(
    monkeypatch: pytest.MonkeyPatch,
    carrier: str,
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
        effects.archived_carrier_absorption(
            Path("/repo"), head="head", accepted_head="accepted", carrier=carrier
        )
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
        policy=policy,
        lane=lane,
        authority_lane=authority,
        accepted_head="b" * 40,
    )
    assert gaps == ["retirement_archive_absorption_stale"]


@pytest.mark.parametrize(
    ("path", "branch", "add_error", "expected"),
    [
        (
            "",
            "work/source",
            False,
            {"state": "blocked", "error": "worktree_restore_coordinates_missing"},
        ),
        (
            "/lane",
            "",
            False,
            {"state": "blocked", "error": "worktree_restore_coordinates_missing"},
        ),
        ("/lane", "work/source", True, {"state": "blocked", "error": "restore rejected"}),
        ("/lane", "work/source", False, {"state": "recognized"}),
    ],
)
def test_restore_worktree_reports_exact_compensation_outcome(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    branch: str,
    add_error: int,
    expected: dict[str, str],
) -> None:
    def add(*_args: object, **_kwargs: object) -> None:
        if add_error:
            message = "restore rejected"
            raise ValueError(message)

    monkeypatch.setattr(effects, "add_worktree", add)

    assert effects.restore_worktree(Path("/control"), _lane(path=path, branch=branch)) == expected


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
