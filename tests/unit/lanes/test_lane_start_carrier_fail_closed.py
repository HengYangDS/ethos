from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_start_carrier as carrier

if TYPE_CHECKING:
    from pathlib import Path


def _result(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(("git",), returncode, stdout, stderr)


@pytest.mark.parametrize(
    ("records", "expected"),
    [
        ("", None),
        ("malformed\0", None),
        ("100644 blob abc\tpath\0", (("100644", "blob", "abc", "path"),)),
    ],
)
def test_tree_entries_fail_closed_on_unreadable_git_tree_records(
    tmp_path: Path, records: str, expected: object
) -> None:
    assert (
        carrier.tree_entries(
            tmp_path,
            "HEAD",
            "openspec/changes/change",
            run=lambda *_a, **_k: _result(0, records),
        )
        == expected
    )


@pytest.mark.parametrize("unsafe", ["120000 blob abc\tpath\0", "100644 tree abc\tpath\0"])
def test_source_carrier_rejects_non_regular_git_objects(tmp_path: Path, unsafe: str) -> None:
    calls = 0

    def run(*_args: object, **_kwargs: object):
        nonlocal calls
        calls += 1
        return _result(0, unsafe)

    failure, tree = carrier.materialize_source_carrier(
        target=tmp_path / "target",
        source_root=tmp_path / "source",
        source_head="head",
        carrier="openspec/changes/change/commitment.toml",
        run=run,
    )

    assert failure is not None
    assert failure.stderr == "source_change_carrier_unsafe"
    assert tree == ""
    assert calls == 1


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        (_result(1, stderr="missing"), None),
        (_result(0, "not-enough-fields\n"), None),
        (
            _result(
                0,
                "a\0a@example.test\0"
                "2026-01-01T00:00:00Z\0c\0c@example.test\0"
                "2026-01-01T00:00:00Z\n",
            ),
            {
                "GIT_AUTHOR_NAME": "a",
                "GIT_AUTHOR_EMAIL": "a@example.test",
                "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
                "GIT_COMMITTER_NAME": "c",
                "GIT_COMMITTER_EMAIL": "c@example.test",
                "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
            },
        ),
    ],
)
def test_lane_start_commit_metadata_is_exact_or_unavailable(
    tmp_path: Path,
    metadata: subprocess.CompletedProcess[str],
    expected: object,
) -> None:
    assert carrier.commit_metadata(tmp_path, "head", run=lambda *_a, **_k: metadata) == expected


def test_fresh_carrier_compensates_when_staging_rejects_generated_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    context = type(
        "Context",
        (),
        {
            "target": tmp_path / "target",
            "source_change_id": "change",
            "source_commitment_path": "openspec/changes/change/commitment.toml",
            "source_root": tmp_path / "commitment.toml",
            "run": staticmethod(lambda *_a, **_k: _result(0, "tree")),
        },
    )()
    context.target.mkdir()
    context.source_root.write_text('id = "change:change"\n')
    monkeypatch.setattr(carrier, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        carrier,
        "run_json",
        lambda *_a, **_k: {
            "exit_code": 0,
            "parse_error": "",
            "json": {"changeName": "change"},
        },
    )
    monkeypatch.setattr(
        carrier,
        "stage_git_paths",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("git_stage_path_outside_repository")),
    )

    failure, tree = carrier.materialize_fresh_carrier(context)

    assert failure is not None
    assert failure.stderr == "git_stage_path_outside_repository"
    assert tree == ""
