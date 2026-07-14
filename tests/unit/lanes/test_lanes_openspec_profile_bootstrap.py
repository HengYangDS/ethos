from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.lifecycle.core as openspec_lifecycle
import ethos.adapters.openspec.lifecycle.scope as openspec_scope
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lanes import start_work_lane
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def _official_open_spec_result(
    args: tuple[str, ...], changes: list[dict[str, object]]
) -> dict[str, object]:
    """Return one minimal official OpenSpec result for bootstrap admission tests."""
    payloads: dict[tuple[str, ...], dict[str, object]] = {
        ("doctor", "--json"): {"root": {"healthy": True}},
        ("list", "--json"): {"changes": changes},
        ("status", "--change", "matching", "--json"): {
            "isComplete": True,
            "schemaName": "spec-driven",
        },
        ("validate", "--all", "--strict", "--json"): {
            "items": [],
            "summary": {"totals": {"failed": 0}},
        },
        ("archive", "matching", "--yes", "--json"): {"archive": {"change": "matching"}},
    }
    return {
        "command": ["openspec", *args],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "json": payloads.get(args, {}),
        "parse_error": "",
    }


def test_prewrite_bootstraps_only_tracked_legacy_profile_material_declaration(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A legacy adopter may add only its missing profile declaration first."""
    repo = init_repo(tmp_path / "repo")
    profile_path = repo / ".ethos" / "profile.toml"
    profile_path.parent.mkdir(exist_ok=True)
    profile_path.write_text('profile_id = "legacy-adopter"\n', encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add legacy adopted profile")
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    worktree = tmp_path / "repo-work-owned"
    start_work_lane(
        root=repo,
        name="owned",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    (worktree / "openspec" / "changes" / "matching").mkdir(parents=True)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda _root, _base, args: _official_open_spec_result(
            args, [{"name": "matching", "status": "in-progress"}]
        ),
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "active_claim_openspec_carriers",
        lambda _root: {"openspec/changes/matching"},
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "proposal_protocol_report",
        lambda _root, _change: {"ok": True, "required_gaps": []},
    )

    profile = worktree / ".ethos" / "profile.toml"
    admitted = prewrite_guard(
        root=worktree,
        paths=[profile],
        editor_root=worktree,
        require_editor_root=True,
    )
    widened = prewrite_guard(
        root=worktree,
        paths=[profile, worktree / "openspec" / "changes" / "matching" / "scope.toml"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert admitted["ok"] is True
    assert admitted["material_scope"]["state"] == "profile_material_paths_bootstrap"
    assert admitted["material_scope"]["profile_bootstrap"] == {
        "change": "matching",
        "profile_path": ".ethos/profile.toml",
    }
    assert widened["ok"] is False
    assert widened["error"] == "openspec_material_paths_missing"


def test_profile_material_paths_bootstrap_rejects_empty_or_untracked_profiles(
    tmp_path: Path,
) -> None:
    """The one-time path does not weaken explicit fail-closed profile states."""
    repo = init_repo(tmp_path / "repo")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text("[openspec]\nmaterial_paths = []\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add explicit empty declaration")

    (repo / "openspec" / "changes" / "matching").mkdir(parents=True)
    empty = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=(".ethos/profile.toml",),
        active_change_names=("matching",),
    )
    profile.write_text('profile_id = "untracked"\n', encoding="utf-8")
    git(repo, "rm", "--cached", ".ethos/profile.toml")
    untracked = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=(".ethos/profile.toml",),
        active_change_names=("matching",),
    )

    assert empty["state"] == "material_paths_missing"
    assert empty["profile_bootstrap"] == {}
    assert untracked["state"] == "material_paths_missing"
    assert untracked["profile_bootstrap"] == {}


def test_profile_material_paths_bootstrap_requires_exactly_one_active_change(
    tmp_path: Path,
) -> None:
    """A legacy profile never chooses between multiple candidate Changes."""
    repo = init_repo(tmp_path / "repo")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text('profile_id = "legacy-adopter"\n', encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add legacy adopted profile")
    for name in ("first", "second"):
        (repo / "openspec" / "changes" / name).mkdir(parents=True)

    report = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=(".ethos/profile.toml",),
        active_change_names=("first", "second"),
    )

    assert report["state"] == "material_paths_missing"
    assert report["profile_bootstrap"] == {}
    assert report["required_gaps"] == ["openspec_material_paths_missing"]
