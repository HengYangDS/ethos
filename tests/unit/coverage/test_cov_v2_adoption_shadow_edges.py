# ruff: noqa: ARG005, TC002, TC003
"""Coverage-closure v2: adoption evolution/retirement and shadow parity edges.

Exercises defensive gap-emitting branches with no prior coverage: campaign
manifest validation gaps, retirement helper fallbacks, and shadow-parity
projection/normalization edges. All target lines are executed through real
production code paths (helper dicts built by production builders, or the public
``run_shadow_parity`` driver with its subprocess runners stubbed).
"""

from __future__ import annotations

import os
import types
from pathlib import Path

import pytest

from ethos.adapters import shadow
from ethos.repository.adoption import evolution
from ethos.repository.adoption import retirement

# --- repository/adoption/evolution.py ---------------------------------------


def _campaign(root: Path, payload: dict[str, object]) -> dict[str, object]:
    """Build a campaign structure through the production payload builder."""
    cid = str(payload.get("id") or "cid")
    path = root / "evolution" / "campaigns" / cid / "campaign.toml"
    return evolution._campaign_payload(root, path, payload)


def test_campaign_manifests_absent_root_returns_empty(tmp_path: Path) -> None:
    # No evolution/campaigns directory short-circuits to empty results (line 83).
    assert evolution._campaign_manifests(tmp_path, campaign_id=None) == ([], [])


def test_campaign_required_gaps_flags_missing_campaign_field(tmp_path: Path) -> None:
    # A blank campaign field (owner) surfaces a required gap (lines 207-208).
    campaign = _campaign(tmp_path, {"id": "cid", "owner": "", "objective": "obj", "claim_id": "cl"})
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_owner_missing:cid" in gaps


def test_campaign_required_gaps_flags_duplicate_step_id(tmp_path: Path) -> None:
    # Two steps sharing an id collapse in the id map, flagging a duplicate (lines 211-212).
    campaign = _campaign(
        tmp_path,
        {
            "id": "cid",
            "owner": "o",
            "objective": "obj",
            "claim_id": "cl",
            "step": [{"id": "s1", "state": "planned"}, {"id": "s1", "state": "planned"}],
        },
    )
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_step_id_duplicate:cid" in gaps


def test_campaign_required_gaps_flags_non_serial_active_steps(tmp_path: Path) -> None:
    # More than one active step violates strict-serial lane topology (lines 213-214).
    campaign = _campaign(
        tmp_path,
        {
            "id": "cid",
            "owner": "o",
            "objective": "obj",
            "claim_id": "cl",
            "step": [{"id": "s1", "state": "active"}, {"id": "s2", "state": "active"}],
        },
    )
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_active_step_not_serial:cid" in gaps


def test_campaign_required_gaps_flags_missing_step_field(tmp_path: Path) -> None:
    # A planned step with a blank required field (title) surfaces a gap (lines 218-219).
    campaign = _campaign(
        tmp_path,
        {
            "id": "cid",
            "owner": "o",
            "objective": "obj",
            "claim_id": "cl",
            "step": [
                {
                    "id": "s1",
                    "state": "planned",
                    "title": "",
                    "openspec_change": "x",
                    "work_lane": "w",
                    "claim_id": "c",
                }
            ],
        },
    )
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_step_title_missing:cid:s1" in gaps


def test_campaign_required_gaps_flags_dependency_not_retired(tmp_path: Path) -> None:
    # An active step depending on a non-retired predecessor is flagged (lines 232-233).
    campaign = _campaign(
        tmp_path,
        {
            "id": "cid",
            "owner": "o",
            "objective": "obj",
            "claim_id": "cl",
            "step": [
                {"id": "s1", "state": "planned"},
                {"id": "s2", "state": "active", "depends_on": ["s1"]},
            ],
        },
    )
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_step_dependency_not_retired:cid:s2:s1" in gaps


def test_campaign_required_gaps_flags_incomplete_closeout_state(tmp_path: Path) -> None:
    # A closed step whose closeout is not closed/retired is incomplete (lines 236-240).
    campaign = _campaign(
        tmp_path,
        {
            "id": "cid",
            "owner": "o",
            "objective": "obj",
            "claim_id": "cl",
            "step": [{"id": "s1", "state": "closed", "closeout": {"state": "planned"}}],
        },
    )
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_step_closeout_state_incomplete:cid:s1" in gaps


def test_campaign_required_gaps_flags_closeout_head_and_evidence(tmp_path: Path) -> None:
    # A closed closeout missing heads and evidence surfaces both gaps (lines 244, 246).
    campaign = _campaign(
        tmp_path,
        {
            "id": "cid",
            "owner": "o",
            "objective": "obj",
            "claim_id": "cl",
            "step": [
                {
                    "id": "s1",
                    "state": "active",
                    "closeout": {
                        "state": "closed",
                        "accepted_head": "",
                        "candidate_head": "",
                        "evidence": [],
                    },
                }
            ],
        },
    )
    gaps = evolution._campaign_required_gaps(tmp_path, campaign)
    assert "campaign_step_closeout_head_missing:cid:s1" in gaps
    assert "campaign_step_closeout_evidence_missing:cid:s1" in gaps


# --- repository/adoption/retirement.py --------------------------------------


def test_binding_checks_flags_non_generic_manifest(tmp_path: Path) -> None:
    # A binding manifest other than .ethos/profile.toml is not generic (lines 126-127).
    checks = retirement._binding_checks(tmp_path, {"binding_manifest": "custom.toml"})
    assert "retirement_binding_manifest_not_generic:custom.toml" in checks["required_gaps"]


def test_lifecycle_stage_reports_embedded_not_frozen() -> None:
    # External default + non-frozen embedded (parity/shadow ok) stalls at embedded (line 456).
    stage = retirement._lifecycle_stage(
        external_state="default",
        embedded_state="active",
        parity_ok=True,
        shadow_ok=True,
    )
    assert stage == "embedded_not_frozen"


def test_object_list_non_list_returns_empty() -> None:
    # A non-list value yields an empty object list (lines 510-511).
    assert retirement._object_list(None) == []


def test_int_value_unparseable_string_returns_zero() -> None:
    # A non-numeric string raises ValueError and falls back to zero (lines 521-522).
    assert retirement._int_value("notanumber") == 0


def test_git_tracked_rejects_path_outside_repo(tmp_path: Path) -> None:
    # An absolute path resolves outside the repo, short-circuiting to False (lines 538-539).
    assert retirement._git_tracked(tmp_path, "/etc/passwd") is False


def test_git_commit_reachable_empty_commit_is_false(tmp_path: Path) -> None:
    # An empty commit reference is trivially unreachable (lines 550-551).
    assert retirement._git_commit_reachable(tmp_path, "") is False


# --- adapters/shadow.py ------------------------------------------------------


def _verdict(command: tuple[str, ...], *, ok: bool, gaps: list[str]) -> dict[str, object]:
    return {"ok": ok, "command": " ".join(command), "required_gaps": gaps}


def test_run_shadow_parity_flags_external_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A non-verdict external result marks the command failed (line 78). Scoped to a
    # single command with both runners stubbed for a deterministic, subprocess-free run.
    monkeypatch.setattr(shadow, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(
        shadow,
        "_run_external",
        lambda t, c, *, timeout_seconds: {
            "exit_code": 2,
            "stdout": "",
            "stderr": "boom",
            "json": {},
        },
    )
    monkeypatch.setattr(
        shadow,
        "_run_embedded",
        lambda t, c, *, timeout_seconds: {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": _verdict(c, ok=True, gaps=[]),
            "required_gaps": [],
        },
    )
    result = shadow.run_shadow_parity(tmp_path, product_root=tmp_path)
    assert "external_command_failed:status" in result["required_gaps"]


def test_run_shadow_parity_flags_false_negative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Embedded reports a blocking gap the external backend does not: a false negative
    # (line 85). Neither process fails, isolating the false-negative branch.
    monkeypatch.setattr(shadow, "READ_ONLY_COMMANDS", (("status",),))
    monkeypatch.setattr(
        shadow,
        "_run_external",
        lambda t, c, *, timeout_seconds: {
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "json": _verdict(c, ok=True, gaps=[]),
        },
    )
    monkeypatch.setattr(
        shadow,
        "_run_embedded",
        lambda t, c, *, timeout_seconds: {
            "exit_code": 1,
            "stdout": "",
            "stderr": "",
            "json": _verdict(c, ok=False, gaps=["embedded_only_gap"]),
            "required_gaps": [],
        },
    )
    result = shadow.run_shadow_parity(tmp_path, product_root=tmp_path)
    assert "shadow_false_negative:status" in result["required_gaps"]
    assert result["false_negative_count"] == 1


def test_changed_paths_skips_blank_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A blank porcelain line is skipped by the continue guard (lines 225-226).
    def _fake_run(_cmd: list[str], *_args: object, **_kwargs: object) -> object:
        return types.SimpleNamespace(
            returncode=0, stdout="?? kept.txt\n\n?? other.txt\n", stderr=""
        )

    monkeypatch.setattr(shadow.subprocess, "run", _fake_run)
    assert shadow._changed_paths(tmp_path) == ["kept.txt", "other.txt"]


def test_evidence_input_non_file_non_dir_returns_none(tmp_path: Path) -> None:
    # A FIFO exists but is neither file nor directory, so it is skipped (lines 254-255).
    os.mkfifo(tmp_path / "fifo")
    assert shadow._evidence_input(tmp_path, "fifo") is None


def test_pyproject_tool_non_dict_tool_returns_empty(tmp_path: Path) -> None:
    # A parseable pyproject with no [tool] table yields an empty tool map (lines 401-402).
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    assert shadow._pyproject_tool(tmp_path) == {}


def test_accepted_difference_unknown_kind_is_unclassified() -> None:
    # An unrecognized accepted-difference kind falls to the unknown branch (lines 634-635).
    difference = shadow._accepted_difference("mystery", command="status", gaps=["g"])
    assert difference["scope"] == "unknown"
    assert difference["reason"] == "unclassified accepted difference"


def test_semantic_state_falls_through_to_raw_state() -> None:
    # ok with no string state and an unknown command returns the raw state (line 786).
    assert shadow._semantic_state({"ok": True}, summary={}, command="mystery") is None


def test_ready_state_for_command_unknown_returns_none() -> None:
    # An unknown command has no canonical ready state (line 806).
    assert shadow._ready_state_for_command("mystery") is None
