"""An exit applies its previewed plan in a fenced order, or leaves the repository as it was."""

from __future__ import annotations

import hashlib
import json
import shlex
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.repo.hook.exit as repository_exit
from ethos.adapters.repo.config_effects import config_values
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.hook.activation import ACTIVATION_KEYS
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.domain.adoption import adopt_repository
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case
from tests.support.runtime_scenarios import materialized_activation_case

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.result import EthosResult


def _apply(repo: Path, **overrides: Any) -> EthosResult:
    request: dict[str, Any] = {
        "apply": True,
        "authorize": True,
        "expect_head": current_head(repo),
        "expect_plan_digest": repository_exit.exit_preview(repo)["plan_digest"],
    }
    return adopt_repository(repo, exit_repository=True, **(request | overrides))


def _state(repo: Path, common: Path) -> dict[str, object]:
    files = {
        path.relative_to(common).as_posix(): path.read_bytes()
        for path in sorted((common / "ethos").rglob("*"))
        if path.is_file() and not path.name.endswith(".lock")
    }
    return {"files": files, "config": config_values(repo, ACTIVATION_KEYS, scope="local")}


def _adopted_with_own_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path, dict[str, tuple[str, ...]]]:
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    assert git_process(repo, "config", "--local", "core.hooksPath", ".githooks").returncode == 0
    before = config_values(repo, ACTIVATION_KEYS, scope="local")
    install_hook_launchers(repo)
    return repo, common, before


def test_an_exit_restores_the_recorded_configuration_and_removes_the_selectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The repository is back at its own configuration, and the receipt holds what changed."""
    repo, common, before = _adopted_with_own_hooks(tmp_path, monkeypatch)
    selector = common / "ethos/runtime/CURRENT"
    current_sha256 = hashlib.sha256(selector.read_bytes()).hexdigest()
    rollback = common / "ethos/runtime/ROLLBACK"
    rollback.write_bytes(selector.read_bytes())
    ethos_hooks = config_values(repo, ("core.hooksPath",), scope="local")["core.hooksPath"]

    result = _apply(repo)

    assert result.state == "applied", result.to_json()
    assert config_values(repo, ACTIVATION_KEYS, scope="local") == before
    assert not selector.exists()
    assert not rollback.exists()
    assert not (common / "ethos/hooks-preimage.json").exists()
    receipt = json.loads((common / "ethos/exit-receipt.json").read_text(encoding="utf-8"))
    assert receipt["selectors"]["CURRENT"]["sha256"] == current_sha256
    assert receipt["configuration"]["before"]["common"]["core.hooksPath"] == list(ethos_hooks)
    assert receipt["configuration"]["after"]["common"]["core.hooksPath"] == [".githooks"]
    data = json.loads(result.to_json())["data"]
    cleanup = data["generation_cleanup"]
    named = {*cleanup["removed"], *cleanup["retained"], *cleanup.get("deferred", [])}
    assert cleanup["checked"]
    assert set(cleanup["checked"]) <= named
    assert data["residue"] == sorted({*cleanup["retained"], *cleanup.get("deferred", [])})


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
    repo, common, _before = _adopted_with_own_hooks(tmp_path, monkeypatch)
    before = _state(repo, common)

    result = _apply(repo, **overrides)

    assert result.state == "blocked"
    assert gap in result.required_gaps
    assert _state(repo, common) == before


def test_a_failed_exit_compensates_exactly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A selector that cannot be removed returns the configuration, selectors and record."""
    repo, common, _before = _adopted_with_own_hooks(tmp_path, monkeypatch)
    before = _state(repo, common)
    runtime = common / "ethos/runtime"
    runtime.chmod(0o555)
    try:
        result = _apply(repo)
    finally:
        runtime.chmod(0o755)

    assert result.state == "blocked", result.to_json()
    assert result.required_gaps[0].startswith("adoption_exit_failed:")
    assert _state(repo, common) == before


def test_an_exit_keeps_worktree_configuration_while_a_worktree_has_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git ignores a worktree's own configuration without the extension, so it stays enabled."""
    repo, linked, _runtime, _hooks = linked_runtime_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    assert git_process(linked, "config", "--worktree", "user.name", "lane").returncode == 0

    result = _apply(repo)

    assert result.state == "applied", result.to_json()
    kept = config_values(repo, ("extensions.worktreeConfig", "core.hooksPath"), scope="local")
    assert kept == {"extensions.worktreeConfig": ("true",), "core.hooksPath": ()}


def test_status_reports_the_exit_from_its_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After an exit, status names it; a repository without a profile no longer needs hooks."""
    repo, common, _before = _adopted_with_own_hooks(tmp_path, monkeypatch)
    assert "exit" not in hook_runtime_binding(repo)

    assert _apply(repo).state == "applied"
    binding = hook_runtime_binding(repo)

    assert binding["exit"]["state"] == "exited"
    assert binding["exit"]["receipt"] == (common / "ethos/exit-receipt.json").as_posix()
    assert binding["required"] is False


def test_ethos_adopt_exit_applies_the_previewed_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview's next action is the exact apply request, and it exits the repository."""
    repo, common, _before = _adopted_with_own_hooks(tmp_path, monkeypatch)
    preview = json.loads(run_ethos_raw("adopt", "--exit", "--json", "--root", str(repo)).stdout)
    request = shlex.split(preview["next_action"])

    applied = run_ethos_raw(*request[1:])

    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert json.loads(applied.stdout)["state"] == "applied"
    assert not (common / "ethos/runtime/CURRENT").exists()
