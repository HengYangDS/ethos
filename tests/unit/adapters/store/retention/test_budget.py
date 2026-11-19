"""A store's bytes are reported against its declared budget, and a budget refuses nothing."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

import ethos.application.retention as retention
from ethos.adapters.store.retention.budget import budget_row
from ethos.adapters.store.retention.budget import owned_budget
from ethos.adapters.store.retention.budget import store_report
from ethos.adapters.store.retention.budget import tree_bytes
from ethos.adapters.store.state.schema import local_state_root
from tests.support.closed_directory import NEEDS_A_CLOSED_DIRECTORY
from tests.support.ethos_cli_runner import full_result
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_process
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.retention_store import proof_check
from tests.support.retention_store import put


def test_the_report_counts_regular_files_by_name_and_follows_no_link(tmp_path: Path) -> None:
    """Nested files count under their top-level name; a link adds nothing, whatever it names."""
    store, outside = tmp_path / "store", tmp_path / "outside"
    (store / "artifacts/nested").mkdir(parents=True)
    outside.mkdir()
    (outside / "large").write_bytes(b"x" * 4096)
    (store / "artifacts/one").write_bytes(b"x" * 10)
    (store / "artifacts/nested/two").write_bytes(b"x" * 20)
    (store / "artifacts/file-link").symlink_to(outside / "large")
    (store / "artifacts/tree-link").symlink_to(outside, target_is_directory=True)
    (store / "top-link").symlink_to(outside, target_is_directory=True)
    (store / "state.sqlite").write_bytes(b"x" * 5)

    report = store_report(store)

    assert report["names"] == {
        "artifacts": {"files": 2, "bytes": 30, "unread": 0},
        "state.sqlite": {"files": 1, "bytes": 5, "unread": 0},
        "top-link": {"files": 0, "bytes": 0, "unread": 0},
    }
    assert datetime.fromisoformat(report["read_at"]).utcoffset().total_seconds() == 0
    assert report["unread"] == 0
    absent = store_report(tmp_path / "absent")
    assert (absent["names"], absent["unread"]) == ({}, 0)


@NEEDS_A_CLOSED_DIRECTORY
def test_a_directory_that_cannot_be_read_is_counted_and_the_rest_is_reported(
    tmp_path: Path,
) -> None:
    """The walk goes on past a closed directory and says how many it could not read."""
    closed = tmp_path / "custody/closed"
    closed.mkdir(parents=True)
    (tmp_path / "custody/kept").write_bytes(b"x" * 7)
    closed.chmod(0)
    try:
        assert tree_bytes(tmp_path / "custody") == {"files": 1, "bytes": 7, "unread": 1}
        assert tree_bytes(closed / "below") == {"files": 0, "bytes": 0, "unread": 1}
        shut = store_report(closed)
    finally:
        closed.chmod(0o700)
    assert (shut["names"], shut["unread"]) == ({}, 1)


@NEEDS_A_CLOSED_DIRECTORY
def test_a_file_whose_status_cannot_be_read_is_counted_and_the_row_says_unread(
    tmp_path: Path,
) -> None:
    """A listed name that cannot be read is a place not read; nothing at a path is none."""
    listed = tmp_path / "artifacts"
    listed.mkdir()
    (listed / "kept").write_bytes(b"x" * 7)
    listed.chmod(0o400)
    try:
        assert tree_bytes(listed) == {"files": 0, "bytes": 0, "unread": 1}
        row = owned_budget(tmp_path, 16)
    finally:
        listed.chmod(0o700)
    assert row == {"bytes": 0, "budget_bytes": 16, "state": "unread", "unread": 1}
    assert tree_bytes(tmp_path / "absent") == {"files": 0, "bytes": 0, "unread": 0}
    assert tree_bytes(listed / "kept/below") == {"files": 0, "bytes": 0, "unread": 0}


@NEEDS_A_CLOSED_DIRECTORY
@pytest.mark.parametrize("closed", ["operations", "operations/lane-retirement"])
def test_an_owned_place_that_the_host_will_not_answer_for_is_a_place_not_read(
    tmp_path: Path, closed: str
) -> None:
    """A candidate under a closed parent, or one that cannot be listed, leaves the row `unread`."""
    (tmp_path / "operations/lane-retirement/unit").mkdir(parents=True)
    (tmp_path / "operations/lane-retirement/unit/kept").write_bytes(b"x" * 7)
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts/kept").write_bytes(b"x" * 5)
    (tmp_path / closed).chmod(0)
    try:
        row = owned_budget(tmp_path, 16)
    finally:
        (tmp_path / closed).chmod(0o700)
    assert row == {"bytes": 5, "budget_bytes": 16, "state": "unread", "unread": 1}
    assert owned_budget(tmp_path, 16) == {
        "bytes": 12,
        "budget_bytes": 16,
        "state": "within",
        "unread": 0,
    }


@pytest.mark.parametrize(
    ("held", "unread", "state"),
    [(16, 0, "within"), (17, 0, "over"), (16, 2, "unread"), (17, 2, "over")],
)
def test_a_row_is_over_only_above_its_budget_and_never_within_on_an_incomplete_read(
    held: int, unread: int, state: str
) -> None:
    """A missed place can only add bytes: counted bytes above the budget stay `over`."""
    row = {"bytes": held, "budget_bytes": 16, "state": state, "unread": unread}
    assert budget_row(held, 16, unread) == row


def test_a_row_that_is_over_changes_nothing_else_in_the_preview(repo: Path) -> None:
    """Under a lower declared budget the same store is over; the rest of the result is equal."""
    store = local_state_root(repo)
    young = put(store, "artifacts", proof_check(), ".json", age_days=1)
    held = young.stat().st_size

    within = retention.preview_record_retirement(repo)
    (repo / ".ethos/rules.toml").write_text("[paradigm.retention]\nstatus_bytes = 1\n")
    commit_fixture(repo, "declare a lower store budget")
    over = retention.preview_record_retirement(repo)

    kept = {"verdict", "state", "required_gaps", "next_action"}
    row = {"bytes": held, "unread": 0}
    assert within.summary["budget"] == row | {"budget_bytes": 2**30, "state": "within"}
    assert over.summary["budget"] == row | {"budget_bytes": 1, "state": "over"}
    assert over.model_dump(include=kept) == within.model_dump(include=kept)
    assert over.data["store"]["names"]["artifacts"] == {"files": 1, "bytes": held, "unread": 0}


@pytest.mark.parametrize("switch", [(), ("--release-absent",)])
def test_the_supply_preview_reports_the_host_installations(
    tmp_path: Path, switch: tuple[str, ...]
) -> None:
    """With and without the switch the summary holds the row; a lower declared value is over.

    The lowered case runs the console in a fresh process, which binds the parameters of the
    repository that `--root` names.
    """
    installation = Path(os.environ["XDG_DATA_HOME"]) / "ethos/installations" / ("9" * 16)
    (installation / "runtime").mkdir(parents=True)
    (installation / "runtime/payload").write_bytes(b"x" * 2048)
    repository = init_git_repo(tmp_path / "projects/repository")
    words = ("hook", "retire-supply", "--scan", str(tmp_path / "projects"), *switch)

    default = run_ethos(*words, "--root", str(repository), "--json")
    (repository / ".ethos").mkdir(exist_ok=True)
    (repository / ".ethos/rules.toml").write_text("[paradigm.retention]\nhost_bytes = 1024\n")
    completed = run_ethos_process(*words, "--root", str(repository), "--json")
    lowered = full_result(completed)

    row = {"bytes": 2048, "unread": 0}
    assert completed.returncode == 0, completed.stderr
    assert default["summary"]["budget"] == row | {"budget_bytes": 4 * 2**30, "state": "within"}
    assert lowered["summary"]["budget"] == row | {"budget_bytes": 1024, "state": "over"}
    assert (lowered["verdict"], lowered["state"]) == (default["verdict"], default["state"])


@NEEDS_A_CLOSED_DIRECTORY
def test_the_supply_row_says_unread_when_an_installation_cannot_be_read(tmp_path: Path) -> None:
    """The preview's row carries the places it could not read, and its verdict stays."""
    runtime = Path(os.environ["XDG_DATA_HOME"]) / "ethos/installations" / ("9" * 16) / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "payload").write_bytes(b"x" * 2048)
    repository = init_git_repo(tmp_path / "projects/repository")
    words = ("hook", "retire-supply", "--scan", str(tmp_path / "projects"))
    runtime.chmod(0o400)
    try:
        preview = run_ethos(*words, "--root", str(repository), "--json")
    finally:
        runtime.chmod(0o700)

    row = {"bytes": 0, "budget_bytes": 4 * 2**30, "state": "unread", "unread": 1}
    assert (preview["summary"]["budget"], preview["verdict"]) == (row, "pass")
