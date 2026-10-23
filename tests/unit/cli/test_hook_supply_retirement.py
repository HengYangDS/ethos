"""`ethos hook retire-supply` previews legacy host installations and retires an approved plan."""

from __future__ import annotations

import os
import shlex
import time
from pathlib import Path

from ethos.adapters.repo.runtime.host_store import installation_consumers
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo

MONTH = 30 * 24 * 3600


def _installation(store: Path, digest: str) -> Path:
    installation = store / digest[:16]
    runtime = installation / "runtime" / digest
    runtime.mkdir(parents=True)
    (runtime / "payload").write_bytes(b"x" * 2048)
    (installation / "OWNER").write_text(digest + "\n", encoding="utf-8")
    stamp = time.time() - MONTH
    os.utime(installation, (stamp, stamp))
    return runtime.resolve()


def _case(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """Return a scanned root, its repository, a selected and an unused legacy installation."""
    store = Path(os.environ["XDG_DATA_HOME"]) / "ethos/installations"
    selected = _installation(store, "7" * 64)
    unused = _installation(store, "8" * 64)
    projects = tmp_path / "projects"
    repository = init_git_repo(projects / "repository")
    common = (repository / ".git").resolve()
    (common / "ethos/runtime").mkdir(parents=True, exist_ok=True)
    (common / "ethos/runtime/CURRENT").write_bytes(runtime_selection_bytes(common, selected))
    return projects, repository, selected, unused


def test_the_preview_names_the_retirable_supply_and_asks_for_the_user_decision(
    tmp_path: Path,
) -> None:
    projects, repository, selected, unused = _case(tmp_path)

    preview = run_ethos(
        "hook", "retire-supply", "--scan", str(projects), "--root", str(repository), "--json"
    )

    assert preview["verdict"] == "pass"
    assert preview["user_decision_required"] is True
    assert [row["installation"] for row in preview["data"]["retirable"]] == [
        unused.parents[1].as_posix()
    ]
    assert "--expect-plan" in preview["next_action"]
    assert selected.exists()
    assert unused.exists()


def test_the_previewed_command_retires_exactly_its_plan(tmp_path: Path) -> None:
    projects, repository, selected, unused = _case(tmp_path)
    preview = run_ethos(
        "hook", "retire-supply", "--scan", str(projects), "--root", str(repository), "--json"
    )

    applied = run_ethos(*shlex.split(preview["next_action"])[1:])

    assert applied["verdict"] == "pass"
    assert applied["data"]["retired"] == [unused.parents[1].as_posix()]
    assert not unused.exists()
    assert selected.exists()
    assert installation_consumers(selected.parents[1]) is not None


def test_retirement_needs_authorization_and_an_existing_scan_root(tmp_path: Path) -> None:
    projects, repository, selected, unused = _case(tmp_path)
    preview = run_ethos(
        "hook", "retire-supply", "--scan", str(projects), "--root", str(repository), "--json"
    )
    unauthorized = [
        part for part in shlex.split(preview["next_action"])[1:] if part != "--authorize"
    ]

    refused = run_ethos_blocked(*unauthorized)
    missing = run_ethos_blocked(
        "hook",
        "retire-supply",
        "--scan",
        str(tmp_path / "absent"),
        "--root",
        str(repository),
        "--json",
    )

    assert refused["required_gaps"] == ["authorization_required"]
    assert missing["required_gaps"] == ["host_store_scan_root_invalid"]
    assert selected.exists()
    assert unused.exists()
