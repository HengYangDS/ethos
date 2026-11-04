"""A repository's exit restores what ETHOS replaced, and is previewed before any effect."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.exit as repository_exit
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import exact_lease
from tests.support.runtime_scenarios import git_process
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


def test_an_exit_without_a_record_asks_instead_of_guessing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository adopted before installs recorded anything needs the user's choice."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)
    (common / "ethos/hooks-preimage.json").unlink()

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


def test_the_public_exit_only_previews_in_this_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ethos adopt --exit` reports its plan; an apply is refused until the apply ships."""
    repo, _runtime, _common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)

    result = repository_exit.adopt_exit(repo, apply=True)

    assert result.required_gaps == ("adoption_exit_apply_unavailable",)
    assert json.loads(result.to_json())["data"]["plan_digest"]


def test_ethos_adopt_exit_reports_the_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The public command previews the exit, and refuses to combine it with an adoption."""
    repo, _runtime, _common = materialized_activation_case(tmp_path, monkeypatch)
    install_hook_launchers(repo)

    preview = run_ethos_raw("adopt", "--exit", "--json", "--root", str(repo))
    combined = run_ethos_raw("adopt", "--exit", "--select-runtime", "--json", "--root", str(repo))

    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert json.loads(preview.stdout)["data"]["selectors"]["CURRENT"]["present"] is True
    assert json.loads(combined.stdout)["required_gaps"] == ["adoption_exit_combined_with_adoption"]
