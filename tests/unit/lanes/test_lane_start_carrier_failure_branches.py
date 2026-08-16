from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.mutation.lane_start_carrier as carrier


def _run_result(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, "")


def test_prepare_returns_drift_before_creating_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    context = SimpleNamespace(
        candidate={"head": "a" * 40},
        repo=Path("/repo"),
        source_root=Path("/source"),
        source_branch="",
        source_head="",
        run=lambda *_args, **_kwargs: _run_result(),
    )
    monkeypatch.setattr(carrier, "lane_start_drift_gap", lambda **_kwargs: "candidate_moved")
    monkeypatch.setattr(
        carrier,
        "add_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("effect reached")),
    )
    failure, head, attestation = carrier.prepare_lane_start_carrier(context)
    assert (failure.stderr, head, attestation) == ("candidate_moved", "a" * 40, None)


def test_prepare_converts_worktree_add_error(monkeypatch: pytest.MonkeyPatch) -> None:
    context = SimpleNamespace(
        candidate={"head": "a" * 40},
        repo=Path("/repo"),
        target=Path("/lane"),
        source_root=Path("/source"),
        source_branch="",
        source_head="",
        run=lambda *_args, **_kwargs: _run_result(),
    )
    monkeypatch.setattr(carrier, "lane_start_drift_gap", lambda **_kwargs: "")
    monkeypatch.setattr(
        carrier,
        "add_worktree",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("worktree occupied")),
    )
    failure, head, attestation = carrier.prepare_lane_start_carrier(context)
    assert (failure.stderr, head, attestation) == ("worktree occupied", "a" * 40, None)


def test_complete_lane_start_compensates_hook_binding_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = SimpleNamespace(target=Path("/lane"), branch="work/example")
    monkeypatch.setattr(
        carrier,
        "install_hook_launchers",
        lambda _root: (_ for _ in ()).throw(ValueError("runtime invalid")),
    )
    monkeypatch.setattr(
        carrier.rollback,
        "compensate",
        lambda _context, failed, **kwargs: {"stderr": failed.stderr, **kwargs},
    )
    result = carrier.complete_lane_start(
        context,
        base_head="a" * 40,
        head="b" * 40,
        lease={"lease_id": "lease:test"},
        carrier_attestation=None,
        attachment_attestation=SimpleNamespace(),
    )
    assert result["gap"] == "lane_start_hook_runtime_binding_failed"
    assert result["stderr"] == "runtime invalid"


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"),
    [(1, "", None), (0, "broken", None), (0, "a\0b\0c\0d\0e\0f\n", {"GIT_AUTHOR_NAME": "a"})],
)
def test_commit_metadata_rejects_command_and_shape_failures(
    tmp_path: Path,
    returncode: int,
    stdout: str,
    expected: dict[str, str] | None,
) -> None:
    result = carrier.commit_metadata(
        tmp_path,
        "a" * 40,
        run=lambda *_args, **_kwargs: _run_result(returncode, stdout),
    )
    if expected is None:
        assert result is None
    else:
        assert result is not None
        assert result["GIT_AUTHOR_NAME"] == expected["GIT_AUTHOR_NAME"]


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [(1, ""), (0, "malformed\0"), (0, "")],
)
def test_tree_entries_fails_closed_on_command_shape_or_empty_tree(
    tmp_path: Path, returncode: int, stdout: str
) -> None:
    assert (
        carrier.tree_entries(
            tmp_path,
            "a" * 40,
            "openspec/changes/example",
            run=lambda *_args, **_kwargs: _run_result(returncode, stdout),
        )
        is None
    )


def test_initialize_reports_missing_metadata_and_empty_final_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target"
    target.mkdir()
    subprocess.run(("git", "init", target), check=True, capture_output=True, text=True)
    context = SimpleNamespace(
        candidate={"head": "a" * 40},
        source_head="",
        source_change_id="example",
        source_root=Path("/source"),
        source_branch="",
        repo=target,
        target=target,
        run=lambda *_args, **_kwargs: _run_result(0, ""),
    )
    monkeypatch.setattr(carrier, "materialize_fresh_carrier", lambda _context: (None, "tree"))
    monkeypatch.setattr(carrier, "lane_start_drift_gap", lambda **_kwargs: "")
    monkeypatch.setattr(carrier, "commit_metadata", lambda *_args, **_kwargs: None)
    failure, head = carrier.initialize_lane_carrier(context)
    assert (failure.stderr, head) == ("lane_start_source_commit_metadata_unreadable", "a" * 40)

    monkeypatch.setattr(carrier, "commit_metadata", lambda *_args, **_kwargs: {"A": "B"})
    failure, head = carrier.initialize_lane_carrier(context)
    assert (failure.stderr, head) == ("lane_start_final_head_missing", "")
