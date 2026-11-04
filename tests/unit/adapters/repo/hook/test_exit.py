"""A repository's exit restores what ETHOS replaced, and is previewed before any effect."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest
from filelock import FileLock

import ethos.adapters.repo.hook.exit as repository_exit
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import exact_lease
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case
from tests.support.runtime_scenarios import materialized_activation_case

if TYPE_CHECKING:
    from pathlib import Path


def _hooks_path(repo: Path) -> str:
    completed = git_process(repo, "config", "--local", "--get", "core.hooksPath")
    return completed.stdout.strip()


@pytest.mark.parametrize("own_hooks", [".githooks", None])
def test_install_records_the_configuration_it_replaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, own_hooks: str | None
) -> None:
    """A first adoption keeps the repository's own hooks path, or its absence, for the exit."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    if own_hooks is not None:
        assert git_process(repo, "config", "--local", "core.hooksPath", own_hooks).returncode == 0

    install_hook_launchers(repo)

    record = read_hooks_preimage(common)
    assert record is not None
    assert record["common"]["core.hooksPath"] == ([own_hooks] if own_hooks else [])
    assert _hooks_path(repo).startswith((common / "ethos/hooks").as_posix())


def test_a_reinstall_never_rewrites_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An upgrade replaces only ETHOS's own hooks path, so the first adoption's record stays."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    assert git_process(repo, "config", "--local", "core.hooksPath", ".githooks").returncode == 0
    install_hook_launchers(repo)
    recorded = (common / "ethos/hooks-preimage.json").read_bytes()

    install_hook_launchers(repo)

    assert (common / "ethos/hooks-preimage.json").read_bytes() == recorded


def _state(repo: Path, common: Path) -> dict[str, object]:
    files = {
        path.relative_to(common).as_posix(): path.read_bytes()
        for path in sorted((common / "ethos").rglob("*"))
        if path.is_file() and not path.name.endswith(".lock")
    }
    return {"files": files, "hooks_path": _hooks_path(repo)}


def test_the_exit_preview_plans_the_restoration_without_any_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview names what the exit restores and removes, and changes nothing."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    assert git_process(repo, "config", "--local", "core.hooksPath", ".githooks").returncode == 0
    install_hook_launchers(repo)
    before = _state(repo, common)

    first = repository_exit.exit_preview(repo)
    second = repository_exit.exit_preview(repo)

    assert _state(repo, common) == before
    assert first["required_gaps"] == []
    assert first["restore"]["common"]["core.hooksPath"] == [".githooks"]
    assert first["selectors"]["CURRENT"]["sha256"]
    assert first["plan_digest"] == second["plan_digest"]
    assert first["user_decision_required"] is False


@pytest.mark.parametrize("record", [None, '{"schema_version": 2}'])
def test_an_exit_without_a_record_asks_instead_of_guessing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: str | None
) -> None:
    """A repository adopted before installs recorded anything, or with an unreadable record."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    if record is None:
        (common / "ethos/hooks-preimage.json").unlink()
    else:
        (common / "ethos/hooks-preimage.json").write_text(record, encoding="utf-8")

    preview = repository_exit.exit_preview(repo)

    assert preview["required_gaps"] == ["adoption_exit_preimage_unrecorded"]
    assert preview["user_decision_required"] is True
    assert preview["restore"] is None


def test_a_live_lease_blocks_the_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A Work Lane that still admits effects through these hooks blocks the exit.

    The plan's digest binds the Lease snapshot, so an apply cannot use a plan made before it.
    """
    repo, _runtime, _common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    unleased = repository_exit.exit_preview(repo)["plan_digest"]
    acquire_lease(
        state_database(repo),
        lease=exact_lease(branch="work/live", holder_ref="agent:test:case:agent-a"),
    )

    preview = repository_exit.exit_preview(repo)

    assert "adoption_exit_lease_live:work/live" in preview["required_gaps"]
    assert preview["plan_digest"] != unleased


def test_a_held_selection_blocks_the_exit_and_keeps_its_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selection in progress holds its lock; the probe names it and leaves the lock file."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    lock = common / "ethos/runtime-selection.lock"

    with FileLock(lock):
        held = repository_exit.exit_preview(repo)
    free = repository_exit.exit_preview(repo)

    assert held["required_gaps"] == ["adoption_exit_selection_held"]
    assert free["required_gaps"] == []
    assert lock.is_file()


@pytest.mark.parametrize("history", ["never", "unbound_by_hand"])
def test_a_repository_without_a_selector_or_ethos_hooks_is_not_adopted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, history: str
) -> None:
    """Nothing is left to exit, and the files of a manual unbinding are never read as a record."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    if history == "unbound_by_hand":
        install_hook_launchers(repo)
        assert git_process(repo, "config", "--unset", "core.hooksPath").returncode == 0
        unbound = common / "ethos/unbound-20261104T124254Z"
        unbound.mkdir()
        (common / "ethos/runtime/CURRENT").replace(unbound / "CURRENT")

    preview = repository_exit.exit_preview(repo)

    assert preview["required_gaps"] == ["adoption_exit_not_adopted"]
    assert preview["user_decision_required"] is False
    assert preview["restore"] is None


def test_without_a_record_the_users_own_hooks_path_settles_the_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once the user has set the hooks path, an exit without a record only removes selectors."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    (common / "ethos/hooks-preimage.json").unlink()
    assert git_process(repo, "config", "--local", "core.hooksPath", ".githooks").returncode == 0

    preview = repository_exit.exit_preview(repo)

    assert preview["required_gaps"] == []
    assert preview["restore"] is None
    assert preview["selectors"]["CURRENT"]["present"] is True


def test_a_running_process_that_uses_the_runtime_blocks_the_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A process that still names the runtime would lose it, so the exit waits for it."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    command = (sys.executable, "-c", "import time; time.sleep(60)", str(common / "ethos/runtime"))
    process = subprocess.Popen(command)
    try:
        preview = repository_exit.exit_preview(repo)
    finally:
        process.kill()
        process.wait()

    assert preview["required_gaps"] == ["adoption_exit_runtime_in_use"]


def test_the_preview_lists_the_branches_the_accepted_branch_lacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unlanded lane work is named before the exit removes the hooks that admit it."""
    repo, linked, _runtime, _hooks = linked_runtime_case(tmp_path, monkeypatch)
    assert git_process(repo, "branch", "work/landed").returncode == 0
    install_hook_launchers(repo)
    options = ("-c", "core.hooksPath=/dev/null", "-c", "user.name=t", "-c", "user.email=t@e.st")
    committed = git_process(linked, *options, "commit", "--allow-empty", "-m", "unlanded")
    assert committed.returncode == 0, committed.stderr

    preview = repository_exit.exit_preview(repo)

    assert [branch["branch"] for branch in preview["unlanded_branches"]] == ["work/linked"]


def test_ethos_adopt_exit_reports_the_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The public command previews the exit, and refuses to combine it with an adoption."""
    repo, _runtime, _common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)

    preview = run_ethos_raw("adopt", "--exit", "--json", "--root", str(repo))
    combined = run_ethos_raw("adopt", "--exit", "--select-runtime", "--json", "--root", str(repo))

    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert json.loads(preview.stdout)["data"]["selectors"]["CURRENT"]["present"] is True
    assert json.loads(combined.stdout)["required_gaps"] == ["adoption_exit_combined_with_adoption"]
