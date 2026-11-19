"""A store's bytes are reported against its declared budget, and a budget refuses nothing."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

import ethos.application.retention as retention
from ethos.adapters.store.retention.budget import budget_row
from ethos.adapters.store.retention.budget import store_report
from ethos.adapters.store.retention.budget import tree_bytes
from ethos.adapters.store.state.schema import local_state_root
from ethos.repository.paradigm.parameters import repository_parameters
from tests.support.ethos_cli_runner import run_ethos
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


@pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="a directory that its owner cannot search needs POSIX modes and no superuser",
)
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


@pytest.mark.parametrize(("held", "state"), [(16, "within"), (17, "over")])
def test_a_row_is_over_only_above_its_budget(held: int, state: str) -> None:
    assert budget_row(held, 16) == {"bytes": held, "budget_bytes": 16, "state": state}


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
    assert within.summary["budget"] == {"bytes": held, "budget_bytes": 2**30, "state": "within"}
    assert over.summary["budget"] == {"bytes": held, "budget_bytes": 1, "state": "over"}
    assert over.model_dump(include=kept) == within.model_dump(include=kept)
    assert over.data["store"]["names"]["artifacts"] == {"files": 1, "bytes": held, "unread": 0}


@pytest.mark.parametrize("switch", [(), ("--release-absent",)])
def test_the_supply_preview_reports_the_host_installations(
    tmp_path: Path, switch: tuple[str, ...]
) -> None:
    """With and without the switch the summary holds the row; a lower declared value is over.

    The console binds the repository's parameters to an invocation; the test binds them itself.
    """
    installation = Path(os.environ["XDG_DATA_HOME"]) / "ethos/installations" / ("9" * 16)
    (installation / "runtime").mkdir(parents=True)
    (installation / "runtime/payload").write_bytes(b"x" * 2048)
    repository = init_git_repo(tmp_path / "projects/repository")
    words = ("hook", "retire-supply", "--scan", str(tmp_path / "projects"), *switch)

    default = run_ethos(*words, "--root", str(repository), "--json")
    (repository / ".ethos").mkdir(exist_ok=True)
    (repository / ".ethos/rules.toml").write_text("[paradigm.retention]\nhost_bytes = 1024\n")
    with repository_parameters(repository):
        lowered = run_ethos(*words, "--root", str(repository), "--json")

    assert default["summary"]["budget"] == {
        "bytes": 2048,
        "budget_bytes": 4 * 2**30,
        "state": "within",
    }
    assert lowered["summary"]["budget"] == {"bytes": 2048, "budget_bytes": 1024, "state": "over"}
    assert (lowered["verdict"], lowered["state"]) == (default["verdict"], default["state"])
