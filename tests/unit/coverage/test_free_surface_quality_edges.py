# ruff: noqa: ARG005, TC002
"""Edge coverage for the free-surface quality lane's touched modules.

Exercises the defensive branches that carry no other test, so every touched
source file reaches full line coverage without an in-source exemption.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.repo.dirty.core as repo_dirty
import ethos.adapters.repo.runtime.core as repo_runtime
import ethos.adapters.repo.status.core as status
import ethos.repository.adoption.scaffold.documents.pages as scaffold_pages
import ethos.repository.openspec.audit as openspec_audit
import ethos_core.state.invalid as invalid_states
from ethos_core.quality.proof import policy as proof_policy


def test_taxonomy_path_falls_back_when_no_toml_in_parents(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Resolve the module from a temp location with no system/invalid_states.toml in
    # any parent, so the search loop exhausts and returns the relative fallback.
    fake_module = tmp_path / "a" / "b" / "state" / "invalid.py"
    fake_module.parent.mkdir(parents=True)
    fake_module.write_text("", encoding="utf-8")
    monkeypatch.setattr(invalid_states, "__file__", str(fake_module))
    assert invalid_states._taxonomy_path() == Path("system/invalid_states.toml")


def test_run_state_for_adapter_state_unknown_state_is_executed() -> None:
    # A state that is neither passed/failed/planned falls through to executed.
    result = proof_policy.run_state_for_adapter_state("errored")
    assert result == {"state": "executed", "verdict": "errored", "trust_bearing": False}


def test_source_root_for_module_returns_parent_when_no_workspace_marker(
    tmp_path: Path,
) -> None:
    # No pyproject.toml + product marker anywhere above -> module_path.parent.
    module = tmp_path / "pkg" / "mod.py"
    module.parent.mkdir(parents=True)
    module.write_text("", encoding="utf-8")
    assert repo_runtime._source_root_for_module(module) == module.parent


def test_safe_ref_returns_empty_on_git_failure(tmp_path: Path) -> None:
    # tmp_path is not a git repo, so rev-parse raises CalledProcessError -> "".
    assert status._safe_ref(tmp_path, "HEAD") == ""


def test_porcelain_path_extracts_rename_target() -> None:
    assert repo_dirty._porcelain_path('"old name" -> "new name"') == "new name"


def test_dirty_kind_conflicted_and_deleted() -> None:
    assert repo_dirty._dirty_kind("U", "U") == "conflicted"
    assert repo_dirty._dirty_kind("A", "A") == "conflicted"
    assert repo_dirty._dirty_kind("D", " ") == "deleted"


def test_release_toml_github_profile_appends_host_block() -> None:
    toml = scaffold_pages.release_toml("github")
    assert "[host_profile]" in toml
    assert 'provider = "github"' in toml


def testactive_change_names_in_ref_returns_empty_on_git_failure(
    tmp_path: Path,
) -> None:
    # ls-tree against a nonexistent ref in a non-repo fails -> [].
    assert openspec_audit.active_change_names_in_ref(tmp_path, "no-such-ref") == []


def test_current_branch_role_resolves_from_policy(tmp_path: Path) -> None:
    # A non-repo root resolves an empty current branch to a role string, not a raise.
    assert isinstance(openspec_audit._current_branch_role(tmp_path), str)


def test_protected_branch_report_deduplicates_same_branch_role_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # A policy that resolves two protected roles to the same branch yields the same
    # (branch, role, change) key twice; the second occurrence hits the dedup guard.
    class _Policy:
        release_branch = "shared"
        accepted_branch = "shared"
        candidate_branch = "candidate"

        def role_for_branch(self, branch: str) -> str:
            return "release_root" if branch == "shared" else "candidate"

    monkeypatch.setattr(openspec_audit, "load_branch_role_policy", lambda _root: _Policy())
    monkeypatch.setattr(openspec_audit, "_branch_exists", lambda _root, _branch: True)
    monkeypatch.setattr(
        openspec_audit, "active_change_names_in_ref", lambda _root, _branch: ["change-a"]
    )

    report = openspec_audit.protected_branch_active_change_report(tmp_path, current_branch="work")

    # "shared" contributes exactly one record despite being visited twice.
    shared_records = [r for r in report["records"] if r["branch"] == "shared"]
    assert len(shared_records) == 1


def test_protected_branch_required_gaps_skips_non_dict_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Defensive guard: a malformed (non-dict) record in the report is skipped.
    monkeypatch.setattr(
        openspec_audit,
        "protected_branch_active_change_report",
        lambda _root, *, current_branch: {
            "records": [
                ("not", "a", "dict"),
                {"branch": "release", "role": "release_root", "change": "c", "gap": "g"},
            ]
        },
    )
    gaps = openspec_audit.protected_branch_active_change_required_gaps(
        tmp_path, current_branch="work", roles={"release_root"}
    )
    assert gaps == ["g"]
