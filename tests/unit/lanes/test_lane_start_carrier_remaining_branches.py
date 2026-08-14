from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_start_carrier as carrier
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from pathlib import Path


def _result(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(("git",), returncode, stdout, stderr)


@pytest.mark.parametrize(
    ("records", "checkout", "tree", "expected"),
    [
        (None, _result(), _result(), "source_change_carrier_missing"),
        (
            (("100644", "blob", "oid", "path"),),
            _result(1, stderr="checkout"),
            _result(),
            "checkout",
        ),
        ((("100644", "blob", "oid", "path"),), _result(), _result(1, stderr="tree"), "tree"),
    ],
)
def test_source_carrier_public_failures_preserve_first_git_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    records: object,
    checkout: subprocess.CompletedProcess[str],
    tree: subprocess.CompletedProcess[str],
    expected: str,
) -> None:
    monkeypatch.setattr(carrier, "tree_entries", lambda *_a, **_k: records)
    results = iter((checkout, tree))

    failure, observed = carrier.materialize_source_carrier(
        target=tmp_path,
        source_root=tmp_path,
        source_head="head",
        carrier="openspec/changes/change/commitment.toml",
        run=lambda *_a, **_k: next(results),
    )

    assert failure is not None
    assert expected in failure.stderr
    assert observed == ""


def test_source_carrier_rejects_post_write_tree_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = (("100644", "blob", "oid", "path"),)
    observations = iter((entries, (("100644", "blob", "other", "path"),)))
    monkeypatch.setattr(carrier, "tree_entries", lambda *_a, **_k: next(observations))

    failure, observed = carrier.materialize_source_carrier(
        target=tmp_path,
        source_root=tmp_path,
        source_head="head",
        carrier="openspec/changes/change/commitment.toml",
        run=lambda _root, command, *_a, **_k: _result(
            0, "tree\n" if command == "write-tree" else ""
        ),
    )

    assert failure is not None
    assert failure.stderr == "source_change_carrier_materialization_mismatch"
    assert observed == ""


def _fresh_context(tmp_path: Path) -> SimpleNamespace:
    source = tmp_path / "commitment.toml"
    source.write_text('id = "change:change"\n')
    target = tmp_path / "target"
    target.mkdir()
    return SimpleNamespace(
        target=target,
        source_change_id="change",
        source_commitment_path="openspec/changes/change/commitment.toml",
        source_root=source,
        run=lambda *_a, **_k: _result(0, "tree\n"),
    )


def test_lane_carrier_commit_subject_is_conventional(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_test_profile(repo)
    assert carrier.lifecycle_commit_subject(repo, "materialize", "change") == (
        "chore(openspec): materialize change"
    )


@pytest.mark.parametrize(
    ("command", "created", "status", "gap"),
    [
        (None, {}, {}, "openspec_official_cli_missing"),
        (
            ("openspec",),
            {"exit_code": 1, "parse_error": "", "json": {}},
            {},
            "openspec_change_creation_failed",
        ),
        (
            ("openspec",),
            {"exit_code": 0, "parse_error": "", "json": {}},
            {"exit_code": 0, "parse_error": "", "json": {"changeName": "other"}},
            "openspec_change_validation_failed",
        ),
    ],
)
def test_fresh_carrier_public_validation_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: tuple[str, ...] | None,
    created: dict[str, object],
    status: dict[str, object],
    gap: str,
) -> None:
    context = _fresh_context(tmp_path)
    monkeypatch.setattr(carrier, "openspec_base_command", lambda: command)
    replies = iter((created, status))
    monkeypatch.setattr(carrier, "run_json", lambda *_a, **_k: next(replies))
    monkeypatch.setattr(carrier, "stage_git_paths", lambda *_a, **_k: None)

    failure, tree = carrier.materialize_fresh_carrier(context)

    assert failure is not None
    assert failure.stderr == gap
    assert tree == ""


def test_fresh_carrier_preserves_failed_openspec_child_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _fresh_context(tmp_path)
    command = ("openspec", "new", "change")
    monkeypatch.setattr(carrier, "openspec_base_command", lambda: command)
    monkeypatch.setattr(
        carrier,
        "run_json",
        lambda *_a, **_k: {
            "command": [*command, "fixture-change", "--json"],
            "exit_code": 7,
            "stdout": '{"partial":true}',
            "stderr": "creation rejected",
            "parse_error": "unexpected eof",
            "json": {},
        },
    )

    failure, tree = carrier.materialize_fresh_carrier(context)

    assert failure is not None
    assert failure.args == ("openspec", "new", "change", "fixture-change", "--json")
    assert failure.returncode == 7
    assert failure.stdout == '{"partial":true}'
    assert failure.stderr == "creation rejected"
    assert failure.parse_error == "unexpected eof"
    assert tree == ""


@pytest.mark.parametrize(
    ("candidate_ref", "candidate_worktree", "source_ref", "source_worktree", "gap"),
    [
        ("moved", "candidate", "source", "source", "candidate_head_changed_during_lane_start"),
        (
            "candidate",
            "moved",
            "source",
            "source",
            "candidate_worktree_head_changed_during_lane_start",
        ),
        ("candidate", "candidate", "moved", "source", "source_head_changed_during_lane_start"),
        (
            "candidate",
            "candidate",
            "source",
            "moved",
            "source_worktree_head_changed_during_lane_start",
        ),
    ],
)
def test_lane_start_drift_publicly_names_exact_moved_coordinate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    candidate_ref: str,
    candidate_worktree: str,
    source_ref: str,
    source_worktree: str,
    gap: str,
) -> None:
    candidate_path = tmp_path / "candidate"
    source = tmp_path / "source"
    refs = iter((candidate_ref, source_ref))
    monkeypatch.setattr(carrier, "ref_head", lambda *_a, **_k: next(refs))

    observed = carrier.lane_start_drift_gap(
        repo=tmp_path,
        candidate={"branch": "candidate/dev", "head": "candidate", "worktree_path": candidate_path},
        source_root=source,
        source_branch="work/source",
        source_head="source",
        run=lambda root, *_a, **_k: _result(
            0, candidate_worktree if root == candidate_path else source_worktree
        ),
    )

    assert observed == gap
