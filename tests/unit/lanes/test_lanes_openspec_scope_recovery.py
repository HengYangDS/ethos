"""Regression contract for repairing one tracked malformed scope companion."""

from __future__ import annotations

from ethos.adapters.openspec.lifecycle.scope import material_change_scope_report
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo


def test_tracked_invalid_scope_companion_repairs_only_itself(tmp_path) -> None:
    """A malformed selected companion is repairable without covering siblings."""
    repo = init_repo(tmp_path / "repo")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(
        'profile_id = "scope-recovery-test"\n\n'
        '[openspec]\nmaterial_paths = ["openspec/changes/**"]\n',
        encoding="utf-8",
    )
    scope = repo / "openspec" / "changes" / "selected" / "scope.toml"
    scope.parent.mkdir(parents=True)
    scope.write_text("[scope]\npaths = []\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "track malformed scope")
    selected_path = "openspec/changes/selected/scope.toml"
    proposal_path = "openspec/changes/selected/proposal.md"

    def report(*paths: str) -> dict[str, object]:
        return material_change_scope_report(
            repo, changed_paths=paths, active_change_names=("selected",)
        )

    selected = report(selected_path)
    widened = report(selected_path, proposal_path)
    assert selected["state"] == "tracked_scope_repair_admitted"
    assert selected["recovery"] == {"change": "selected", "scope_path": selected_path}
    assert (
        report("openspec/changes/unselected/scope.toml")["state"] == widened["state"] == "uncovered"
    )
    assert set(widened["uncovered_paths"]) == {proposal_path, selected_path}
