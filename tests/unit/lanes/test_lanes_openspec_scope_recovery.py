"""Regression contract for repairing one tracked malformed scope companion."""

from __future__ import annotations

from ethos.adapters.openspec.lifecycle.scope import material_change_scope_report
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def test_tracked_invalid_scope_companion_repairs_only_itself(tmp_path) -> None:
    """A malformed selected companion is repairable without covering siblings."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["openspec/changes/**"]\n', encoding="utf-8"
    )
    scope = repo / "openspec" / "changes" / "selected" / "scope.toml"
    scope.parent.mkdir(parents=True)
    scope.write_text("[scope]\npaths = []\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "track malformed scope")

    selected = material_change_scope_report(
        repo,
        changed_paths=("openspec/changes/selected/scope.toml",),
        active_change_names=("selected",),
    )
    unselected = material_change_scope_report(
        repo,
        changed_paths=("openspec/changes/unselected/scope.toml",),
        active_change_names=("selected",),
    )
    widened = material_change_scope_report(
        repo,
        changed_paths=(
            "openspec/changes/selected/scope.toml",
            "openspec/changes/selected/proposal.md",
        ),
        active_change_names=("selected",),
    )

    assert selected["state"] == "tracked_scope_repair_admitted"
    assert selected["recovery"] == {
        "change": "selected",
        "scope_path": "openspec/changes/selected/scope.toml",
    }
    assert unselected["state"] == widened["state"] == "uncovered"
    assert set(widened["uncovered_paths"]) == {
        "openspec/changes/selected/proposal.md",
        "openspec/changes/selected/scope.toml",
    }
