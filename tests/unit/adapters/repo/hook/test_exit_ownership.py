"""An exit changes only the keys ETHOS still owns, and its plan names everything it changes."""

from __future__ import annotations

import json
import shlex
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.config_effects import config_values
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.exit_plan import exit_preview
from ethos.adapters.repo.hook.preimage import ethos_owns_hooks_path
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from ethos.application.adoption import adopt_repository
from tests.support.repository_exit import adopted_with_own_hooks
from tests.support.repository_exit import apply_exit
from tests.support.repository_exit import observe_no_foreign_processes
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import linked_runtime_case
from tests.support.runtime_scenarios import materialized_activation_case

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("relative", "owner"),
    [
        ("ethos/hooks/" + "b" * 64, "ethos"),
        ("ethos-hooks", "ethos"),
        ("ethos-hooks-" + "a" * 64, "ethos"),
        ("worktrees/lane/ethos-hooks", "ethos"),
        ("ethos-hooks-manual", "repository"),
        ("../.husky", "repository"),
    ],
)
def test_ethos_owns_its_current_and_legacy_hooks_paths(
    tmp_path: Path, relative: str, owner: str
) -> None:
    """Every layout ETHOS has written is ETHOS's; a neighbour's directory is not."""
    common = tmp_path / ".git"

    owned = ethos_owns_hooks_path(common, ((common / relative).as_posix(),))
    assert owned is (owner == "ethos")
    assert ethos_owns_hooks_path(common, (".husky",)) is False


@pytest.mark.parametrize("legacy", ["ethos-hooks", "ethos-hooks-" + "a" * 64])
def test_a_legacy_ethos_hooks_path_is_never_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, legacy: str
) -> None:
    """A worktree-scoped hooks path from before 2026-08-24 is ETHOS's own, not a preimage."""
    repo, _runtime, common = materialized_activation_case(tmp_path, monkeypatch)
    assert (
        git_process(repo, "config", "--local", "extensions.worktreeConfig", "true").returncode == 0
    )
    path = (common / legacy).as_posix()
    assert git_process(repo, "config", "--worktree", "core.hooksPath", path).returncode == 0

    install_hook_launchers(repo)

    record = read_hooks_preimage(common)
    assert record is not None
    assert all("core.hooksPath" not in entries for entries in record["worktrees"].values())


def test_a_readoption_records_the_hooks_path_it_replaces_now(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale entry gives way to the value install replaces; owned keys keep their entries."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    assert git_process(repo, "config", "--local", "core.hooksPath", ".husky").returncode == 0

    install_hook_launchers(repo)

    record = read_hooks_preimage(common)
    assert record is not None
    assert record["common"]["core.hooksPath"] == [".husky"]
    assert record["common"]["gc.packRefs"] == []


def test_a_hooks_path_set_after_adoption_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Husky installed after adoption owns the hooks path; the exit keeps it and says so."""
    repo, _common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    assert git_process(repo, "config", "--local", "core.hooksPath", ".husky").returncode == 0

    preview = exit_preview(repo)
    result = apply_exit(repo)

    assert preview["kept"]["common"] == {"core.hooksPath": [".husky"]}
    assert result.state == "applied", result.to_json()
    restored = config_values(repo, ("core.hooksPath", "gc.packRefs"), scope="local")
    assert restored == {"core.hooksPath": (".husky",), "gc.packRefs": ()}


def test_a_linked_worktree_gets_back_its_recorded_hooks_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Install cleared the worktree's own value and recorded it; the exit writes it back."""
    repo, linked, _runtime, _hooks = linked_runtime_case(tmp_path, monkeypatch)
    observe_no_foreign_processes(monkeypatch)
    assert (
        git_process(repo, "config", "--local", "extensions.worktreeConfig", "true").returncode == 0
    )
    assert git_process(linked, "config", "--worktree", "core.hooksPath", "lane").returncode == 0
    install_hook_launchers(repo)
    assert config_values(linked, ("core.hooksPath",), scope="worktree") == {"core.hooksPath": ()}

    result = apply_exit(repo)

    assert result.state == "applied", result.to_json()
    restored = config_values(linked, ("core.hooksPath",), scope="worktree")
    assert restored == {"core.hooksPath": ("lane",)}


def test_an_exit_without_a_record_reports_the_keys_it_leaves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once the user settled the hooks path, ETHOS's other values stay, named in the plan."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    (common / "ethos/hooks-preimage.json").unlink()
    assert git_process(repo, "config", "--local", "--unset-all", "core.hooksPath").returncode == 0

    preview = exit_preview(repo)

    assert preview["required_gaps"] == []
    assert preview["left"]["common"] == {
        "extensions.worktreeConfig": ["true"],
        "gc.packRefs": ["false"],
        "maintenance.pack-refs.enabled": ["false"],
    }


def test_an_unrecorded_hooks_path_names_the_exact_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An adopter from before the record exists is told the Git command that settles it."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    (common / "ethos/hooks-preimage.json").unlink()

    result = adopt_repository(repo, exit_repository=True)

    assert result.required_gaps == ("adoption_exit_preimage_unrecorded",)
    command = ("git", "-C", str(repo.resolve()), "config", "--local", "--unset-all")
    assert shlex.join((*command, "core.hooksPath")) in result.next_action


def test_the_apply_removes_the_planned_generations_and_keeps_one_in_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview binds the removals; an interpreter that still needs the runtime keeps it."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    runtime = next(path for path in (common / "ethos/runtime").iterdir() if len(path.name) == 64)
    (repo / ".venv").mkdir()
    (repo / ".venv/pyvenv.cfg").write_text(f"home = {runtime.as_posix()}\n", encoding="utf-8")

    planned = exit_preview(repo)["generations"]
    data = json.loads(apply_exit(repo).to_json())["data"]

    assert str(runtime) in {entry["path"] for entry in planned["keep"]}
    assert planned["remove"]
    assert sorted(data["generation_cleanup"]["removed"]) == sorted(planned["remove"])
    assert runtime.is_dir()
    assert str(runtime) in data["residue"]
