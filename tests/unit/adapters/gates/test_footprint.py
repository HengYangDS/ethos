"""A proof reports what its attempt left in the lane, as the difference of two observations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.gates.footprint import footprint_report
from ethos.adapters.gates.footprint import observe_lane
from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from tests.support.closed_directory import NEEDS_A_CLOSED_DIRECTORY
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_file

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_an_observation_reads_the_roots_the_kept_homes_and_the_work_names(tmp_path: Path) -> None:
    """Git's listing collapses a nontracked tree to its root; the homes are read file by file."""
    lane = init_git_repo(tmp_path / "lane")
    write_file(lane / "build/evidence/quality/report.json", "x" * 10)
    write_file(lane / "build/ethos/proof.json", "x" * 20)
    write_file(lane / "build/artifacts/python/package.whl", "x" * 30)
    write_file(lane / "build/runtime/work/render/page.html", "x" * 40)
    write_file(lane / "scratch/notes/draft.md", "x" * 50)

    observed = observe_lane(lane)

    assert observed.unavailable == ""
    assert observed.roots >= {"build/", "scratch/"}
    assert {home: sorted(files) for home, files in observed.files.items()} == {
        "build/evidence": ["quality/report.json"],
        "build/ethos": ["proof.json"],
        "build/artifacts": ["python/package.whl"],
    }
    assert observed.files["build/evidence"]["quality/report.json"][0] == 10
    assert observed.work == {"render"}


def test_the_report_is_what_appeared_or_changed_and_empty_when_nothing_did(tmp_path: Path) -> None:
    """A new file, a changed one, a new work name and a new root are reported; the rest is not."""
    lane = init_git_repo(tmp_path / "lane")
    write_file(lane / "build/evidence/kept.json", "x" * 10)
    write_file(lane / "build/evidence/changed.json", "x" * 10)
    write_file(lane / "build/runtime/work/before/file", "x" * 1)
    before = observe_lane(lane)
    assert footprint_report(lane, before) == {}

    write_file(lane / "build/evidence/changed.json", "x" * 25)
    write_file(lane / "build/evidence/quality/new.json", "x" * 100)
    write_file(lane / "build/artifacts/python/package.whl", "x" * 1000)
    write_file(lane / "build/runtime/work/made/file", "x" * 1)
    write_file(lane / ".venv/lib/module.py", "x" * 5)

    assert footprint_report(lane, before) == {
        "machine_evidence_files": 2,
        "machine_evidence_bytes": 125,
        "local_artifact_files": 1,
        "local_artifact_bytes": 1000,
        "work_names": 1,
        "new_roots": 1,
        "homes": {
            "build/evidence": {
                "files": 2,
                "bytes": 125,
                "paths": ["changed.json", "quality/new.json"],
            },
            "build/artifacts": {"files": 1, "bytes": 1000, "paths": ["python/package.whl"]},
        },
        "work": ["made"],
        "roots": [".venv/"],
    }


def test_a_lane_that_cannot_be_listed_reports_why_and_fails_nothing(tmp_path: Path) -> None:
    """Outside a repository the listing fails; the report names that and holds nothing else."""
    assert footprint_report(tmp_path, observe_lane(tmp_path)) == {"unavailable": "git_listing"}


def test_an_observation_that_fails_with_a_value_error_names_itself_and_raises_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git's environment refuses a malformed configuration overlay; the report names that."""
    lane = init_git_repo(tmp_path / "lane")
    before = observe_lane(lane)
    monkeypatch.setenv("GIT_CONFIG_COUNT", "many")

    assert observe_lane(lane).unavailable == "ValueError"
    assert footprint_report(lane, before) == {"unavailable": "ValueError"}


@NEEDS_A_CLOSED_DIRECTORY
def test_a_directory_that_cannot_be_read_is_counted_as_unread(tmp_path: Path) -> None:
    """A closed directory under a kept home is one unread path of the report."""
    lane = init_git_repo(tmp_path / "lane")
    closed = write_file(lane / "build/evidence/quality/report.json", "x").parent
    before = observe_lane(lane)
    closed.chmod(0)
    try:
        report = footprint_report(lane, before)
    finally:
        closed.chmod(0o755)

    assert report == {"unread": 1}


def test_a_report_of_many_paths_keeps_its_counts_inside_the_payload_bound(tmp_path: Path) -> None:
    """The bound moves the paths to the detail and keeps each home's files and bytes inline."""
    lane = init_git_repo(tmp_path / "lane")
    before = observe_lane(lane)
    for index in range(400):
        write_file(lane / f"build/evidence/quality/report-{index:04}.json", "x" * 8)
    report = footprint_report(lane, before)
    result = EthosResult(command="prove", verdict="pass", state="proven", data={"left": report})

    bounded = apply_payload_budget(result, root=tmp_path / "store")

    assert bounded.bound is not None
    assert list(bounded.bound["partial"]) == ["left"]
    assert bounded.data["left"] == {
        "machine_evidence_files": 400,
        "machine_evidence_bytes": 3200,
        "new_roots": 1,
    }
