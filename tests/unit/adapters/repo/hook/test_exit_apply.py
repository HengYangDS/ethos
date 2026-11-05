"""An exit applies its previewed plan in a fenced order, or leaves the repository as it was."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import sqlite3
from contextlib import closing
from contextlib import nullcontext
from typing import TYPE_CHECKING
from typing import Any

import pytest
from filelock import FileLock
from filelock import Timeout

import ethos.adapters.repo.config_effects as config_effects
import ethos.adapters.repo.hook.exit as repository_exit
import ethos.adapters.repo.runtime.retirement as retirement
from ethos.adapters.repo.config_effects import config_values
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.exit_plan import exit_preview
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import exact_lease
from tests.support.repository_exit import adopted_with_own_hooks
from tests.support.repository_exit import apply_exit
from tests.support.repository_exit import exit_state
from tests.support.repository_exit import observe_no_foreign_processes
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case

if TYPE_CHECKING:
    from pathlib import Path


def test_an_exit_restores_the_recorded_configuration_and_removes_the_selectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The repository is back at its own configuration, and the receipt holds what changed."""
    repo, common, before = adopted_with_own_hooks(tmp_path, monkeypatch)
    selector = common / "ethos/runtime/CURRENT"
    current_sha256 = hashlib.sha256(selector.read_bytes()).hexdigest()
    rollback = common / "ethos/runtime/ROLLBACK"
    rollback.write_bytes(selector.read_bytes())
    ethos_hooks = config_values(repo, ("core.hooksPath",), scope="local")["core.hooksPath"]

    result = apply_exit(repo)

    assert result.state == "applied", result.to_json()
    assert config_values(repo, tuple(before), scope="local") == before
    assert not selector.exists()
    assert not rollback.exists()
    assert not (common / "ethos/hooks-preimage.json").exists()
    receipt = json.loads((common / "ethos/exit-receipt.json").read_text(encoding="utf-8"))
    assert receipt["state"] == "applied"
    assert receipt["selectors"]["CURRENT"]["sha256"] == current_sha256
    assert receipt["configuration"]["before"]["common"]["core.hooksPath"] == list(ethos_hooks)
    assert receipt["configuration"]["after"]["common"]["core.hooksPath"] == [".githooks"]
    data = json.loads(result.to_json())["data"]
    cleanup = data["generation_cleanup"]
    assert set(cleanup["removed"]) == set(data["generations"]["remove"])


@pytest.mark.parametrize(
    ("overrides", "gap"),
    [
        ({"authorize": False}, "authorization_required"),
        ({"expect_head": "0" * 40}, "expect_head_mismatch"),
        ({"expect_plan_digest": None}, "adoption_exit_plan_digest_required"),
        ({"expect_plan_digest": "0" * 64}, "adoption_exit_plan_digest_mismatch"),
    ],
)
def test_an_apply_needs_the_exact_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, overrides: dict[str, Any], gap: str
) -> None:
    """Authorization, the current head and the previewed digest admit the effect, or nothing."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    before = exit_state(repo, common)

    result = apply_exit(repo, **overrides)

    assert result.state == "blocked"
    assert gap in result.required_gaps
    assert exit_state(repo, common) == before


def _held_lease(repo: Path) -> None:
    """A Lease whose expiry cannot be read is an unknown Lease, which blocks like a live one."""
    acquire_lease(
        state_database(repo),
        lease=exact_lease(branch="work/live", holder_ref="agent:test:case:agent-a"),
    )
    with closing(sqlite3.connect(state_database(repo))) as connection:
        connection.execute("update leases set expires_at = 'unreadable'")
        connection.commit()


@pytest.mark.parametrize(
    ("blocker", "gap"),
    [
        ("proof_slot", "adoption_exit_proof_running"),
        ("processes", "adoption_exit_runtime_use_unknown"),
        ("lease", "adoption_exit_lease_live:work/live"),
    ],
)
def test_a_blocker_after_the_preview_refuses_the_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocker: str, gap: str
) -> None:
    """The apply observes its blockers again under the fence and changes nothing."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    digest = exit_preview(repo)["plan_digest"]
    slot = FileLock(common / "ethos/proof-slot.lock") if blocker == "proof_slot" else nullcontext()

    def unknown(*_args: object, **_kwargs: object) -> str:
        message = "hook_runtime_consumers_unknown"
        raise ValueError(message)

    if blocker == "processes":
        monkeypatch.setattr(retirement, "process_commands", unknown)
    if blocker == "lease":
        _held_lease(repo)
    before = exit_state(repo, common)
    with slot:
        result = apply_exit(repo, expect_plan_digest=digest)

    assert gap in result.required_gaps, result.to_json()
    assert exit_state(repo, common) == before


def test_a_concurrent_configuration_change_is_never_lost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hooks path written after the plan is not ETHOS's; the exit stops and keeps it."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)

    def remove_while_another_writer_acts(path: Path) -> None:
        if path.name == "hooks-preimage.json":
            assert (
                git_process(repo, "config", "--local", "core.hooksPath", ".husky").returncode == 0
            )
        path.unlink(missing_ok=True)

    monkeypatch.setattr(repository_exit, "_remove", remove_while_another_writer_acts)
    result = apply_exit(repo)

    assert result.required_gaps[0].startswith("adoption_exit_failed:git_config_effect_stale")
    assert config_values(repo, ("core.hooksPath",), scope="local") == {
        "core.hooksPath": (".husky",)
    }
    assert (common / "ethos/runtime/CURRENT").exists()
    assert (common / "ethos/hooks-preimage.json").exists()


def test_a_selector_that_changed_after_the_plan_is_not_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selector written outside the lock is not the planned one, so the exit stops."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    selector = common / "ethos/runtime/CURRENT"

    def remove_while_a_selector_changes(path: Path) -> None:
        if path.name == "hooks-preimage.json":
            selector.write_bytes(b"changed\n")
        path.unlink(missing_ok=True)

    monkeypatch.setattr(repository_exit, "_remove", remove_while_a_selector_changes)
    result = apply_exit(repo)

    assert result.required_gaps == ("adoption_exit_failed:adoption_exit_selector_changed:CURRENT",)
    assert selector.exists()


@pytest.mark.parametrize("failure", ["configuration", "verification"])
def test_a_failed_exit_compensates_exactly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """A failed write or verification returns the configuration, selectors, record and receipt."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    (common / "ethos/runtime/ROLLBACK").write_bytes(b"rollback\n")
    before = exit_state(repo, common)
    real = config_effects.replace_config_values
    writes: list[object] = []

    def fail_second_write(*args: Any, **kwargs: Any) -> None:
        writes.append(args)
        if len(writes) == 2:
            message = "injected"
            raise ValueError(message)
        real(*args, **kwargs)

    def fail_verification(*_args: object) -> None:
        message = "injected"
        raise ValueError(message)

    if failure == "configuration":
        monkeypatch.setattr(config_effects, "replace_config_values", fail_second_write)
    else:
        monkeypatch.setattr(repository_exit, "_require_no_ethos_hooks", fail_verification)
    result = apply_exit(repo)

    assert result.required_gaps == ("adoption_exit_failed:injected",), result.to_json()
    assert result.state == "blocked"
    assert exit_state(repo, common) == before


def test_a_compensation_that_fails_reports_every_failure_as_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every compensation step is attempted, and each one that fails is named."""
    repo, _common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)

    def fail_on_selector(path: Path) -> None:
        if path.name == "CURRENT":
            message = "injected"
            raise OSError(message)
        path.unlink(missing_ok=True)

    def restore_fails(path: Path, _content: bytes | None) -> None:
        message = f"restore failed:{path.name}"
        raise OSError(message)

    monkeypatch.setattr(repository_exit, "_remove", fail_on_selector)
    monkeypatch.setattr(repository_exit, "restore_file", restore_fails)
    result = apply_exit(repo)

    assert result.state == "unknown", result.to_json()
    (gap,) = result.required_gaps
    assert gap.startswith("adoption_exit_compensation_failed:")
    assert "restore failed:hooks-preimage.json" in gap
    assert "restore failed:exit-receipt.json" in gap


class _BusyLock:
    """A selection lock that another selection holds past the declared wait."""

    def __init__(self, path: Path) -> None:
        self.lock_file = str(path)

    def acquire(self, **_kwargs: object) -> nullcontext[None]:
        return nullcontext()

    def __enter__(self) -> None:
        raise Timeout(self.lock_file)

    def __exit__(self, *_exc: object) -> None:
        return None


@pytest.mark.parametrize(
    ("busy", "gap"),
    [("selection", "adoption_exit_selection_busy"), ("state", "adoption_exit_state_busy")],
)
def test_a_busy_fence_is_a_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, busy: str, gap: str
) -> None:
    """A lock or state transaction held past its bound is reported, not raised."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    before = exit_state(repo, common)
    holder = sqlite3.connect(state_database(repo))
    if busy == "selection":
        lock = _BusyLock(common / "ethos/runtime-selection.lock")
        monkeypatch.setattr(repository_exit, "runtime_selection_lock", lambda _common: lock)
    else:
        monkeypatch.setattr(repository_exit, "seconds", lambda _kind: 0.05)
        holder.execute("begin immediate")
    try:
        result = apply_exit(repo)
    finally:
        holder.close()

    assert result.required_gaps == (gap,), result.to_json()
    assert exit_state(repo, common) == before


def test_an_exit_keeps_worktree_configuration_while_a_worktree_has_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git ignores a worktree's own configuration without the extension, so it stays enabled."""
    repo, linked, _runtime, _hooks = linked_runtime_case(tmp_path, monkeypatch)
    observe_no_foreign_processes(monkeypatch)
    install_hook_launchers(repo)
    assert git_process(linked, "config", "--worktree", "user.name", "lane").returncode == 0

    preview = exit_preview(repo)
    result = apply_exit(repo)

    assert preview["after"]["common"]["extensions.worktreeConfig"] == ["true"]
    assert result.state == "applied", result.to_json()
    kept = config_values(repo, ("extensions.worktreeConfig", "core.hooksPath"), scope="local")
    assert kept == {"extensions.worktreeConfig": ("true",), "core.hooksPath": ()}


def test_status_reports_the_exit_from_its_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After an exit, status names it; a repository without a profile no longer needs hooks."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    assert "exit" not in hook_runtime_binding(repo)

    assert apply_exit(repo).state == "applied"
    binding = hook_runtime_binding(repo)

    assert binding["exit"]["state"] == "exited"
    assert binding["exit"]["receipt"] == (common / "ethos/exit-receipt.json").as_posix()
    assert binding["required"] is False


@pytest.mark.skipif(os.name == "nt", reason="a standard Windows user cannot read every process")
def test_ethos_adopt_exit_applies_the_previewed_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview's next action is the exact apply request, and it exits the repository."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    preview = json.loads(run_ethos_raw("adopt", "--exit", "--json", "--root", str(repo)).stdout)
    request = shlex.split(preview["next_action"])

    applied = run_ethos_raw(*request[1:])

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert json.loads(applied.stdout)["state"] == "applied"
    assert not (common / "ethos/runtime/CURRENT").exists()
