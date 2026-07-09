"""Coverage-closure v3: repoadapters reachable branches (100% no-exemption)."""

from __future__ import annotations

import types
from typing import TYPE_CHECKING

import ethos.adapters.repo.status.core as status
import ethos.adapters.shadow.identity as shadow_identity
import ethos.adapters.shadow.semantics as shadow_semantics
from ethos.adapters.repo import coordination
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# --- adapters/repo/coordination.py ------------------------------------------


def test_combined_scope_state_unknown_committed_returns_unknown() -> None:
    # An "unknown" committed state short-circuits before the bounded/empty split (line 114).
    assert coordination._combined_scope_state("unknown", ()) == "unknown"


def test_coordination_package_synthesizes_unbound_refs_from_count() -> None:
    # No explicit refs but a positive count synthesizes placeholder refs (lines 166, 192-199).
    package = coordination.coordination_package(
        [],
        required_gaps=[],
        advisory_gaps=[],
        unbound_work_lane_refs=None,
        unbound_work_lane_count=2,
    )
    assert package["unbound_work_lane_count"] == 2
    refs = package["unbound_work_lane_refs"]
    assert isinstance(refs, list)
    assert len(refs) == 2
    assert all(ref["claim_binding"] == "unbound" for ref in refs)


def test_unknown_unbound_ref_shape() -> None:
    # The synthesized placeholder ref carries blank identity and an inspect action (lines 192-199).
    ref = coordination._unknown_unbound_ref()
    assert ref["branch"] == ""
    assert ref["claim_binding"] == "unbound"
    assert ref["relation_to_accepted"] == "unknown"


def test_coordination_next_action_unknown_scope_before_overlap() -> None:
    # No required gaps but a positive unknown-scope count returns the inspect action (line 214).
    action = coordination.coordination_next_action(
        required_gaps=[],
        overlap_count=1,
        unknown_scope_count=1,
        missing_lease_count=1,
        foreign_work_lane_count=1,
        unbound_work_lane_count=1,
    )
    assert action == "inspect unknown Work Lane scope before candidate integration"


def test_path_overlaps_empty_component_returns_false() -> None:
    # A path that yields no non-empty components cannot overlap anything (line 254).
    assert coordination.path_overlaps("", "a/b") is False
    assert coordination.path_overlaps("/", "a/b") is False


# --- adapters/repo/status/core.py -------------------------------------------


def test_worktrees_skips_blank_lines_with_empty_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A leading blank line finds an empty ``current`` (484->489); the trailing blank line
    # flushes the entry so ``current`` is empty after the loop (492->494).
    porcelain = "\nworktree /linked\nHEAD abcdef\nbranch refs/heads/main\n\n"

    def _stub_run_git(_root: Path, *_args: str) -> str:
        return porcelain

    monkeypatch.setattr(status, "_run_git", _stub_run_git)
    policy = load_branch_role_policy(tmp_path)
    entries = status._worktrees(tmp_path, current_path=tmp_path, policy=policy)
    assert len(entries) == 1
    assert entries[0]["branch"] == "main"
    assert entries[0]["path"] == "/linked"


# --- adapters/shadow/core.py -----------------------------------------------------


def test_changed_paths_skips_empty_rename_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A rename entry whose destination is empty leaves ``raw`` blank, so the append is
    # skipped and the loop continues (branch 230->224).
    def _stub_run(_cmd: list[str], *_args: object, **_kwargs: object) -> types.SimpleNamespace:
        return types.SimpleNamespace(returncode=0, stdout="?? kept.txt\nR  old -> \n", stderr="")

    monkeypatch.setattr(shadow_identity.subprocess, "run", _stub_run)
    assert shadow_identity.changed_paths(tmp_path) == ["kept.txt"]


def test_semantic_projection_unknown_command_root_returns_base() -> None:
    # A command root matching none of the projection branches falls through to the base
    # projection return (branch 720->728).
    projection = shadow_semantics._semantic_projection(("mystery",), {"ok": True})
    assert projection["command"] == "mystery"
    assert "readiness" not in projection
    assert "route_ready" not in projection


def test_mark_projection_ready_unknown_command_is_noop() -> None:
    # A command outside the ready-mark set leaves the projection untouched (branch 741->exit).
    projection: dict[str, object] = {"command": "mystery", "state": "raw"}
    shadow_semantics._mark_projection_ready(projection)
    assert projection == {"command": "mystery", "state": "raw"}
