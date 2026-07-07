# ruff: noqa: ARG005, TC001, TC002, TC003
"""Coverage-closure edge tests for the domain_surface cluster (100% no-exemption campaign)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

# ruff: noqa: ARG005, TC002
from ethos.domain import land
from ethos.domain.orient import _current_head
from ethos.domain.orient import _next_actions
from ethos.surface.cli import quality
from ethos_core.result import EthosResult


def test_land_closeout_audit_root_non_dict_candidate(monkeypatch, tmp_path: Path) -> None:
    # decision.ok is truthy so the guard on line 53 passes, but workspace_status
    # yields a non-dict candidate, driving the isinstance guard to line 57's `return repo`.
    decision = SimpleNamespace(ok=True)
    monkeypatch.setattr(
        land,
        "workspace_status",
        lambda repo: {"candidate": "not-a-dict"},
    )
    assert land.closeout_audit_root(tmp_path, decision) == tmp_path


def test_runner_source_root_fallback_without_source_tree(tmp_path: Path) -> None:
    # No ancestor of this synthetic path has pyproject.toml + packages/ethos/src/ethos/__init__.py,
    # so the loop finds no match and falls through to line 69's `return module_path.parent`.
    module_path = tmp_path / "runner" / "ethos.py"
    assert land._runner_source_root(module_path) == tmp_path / "runner"


def test_current_head_falls_back_to_matching_branch_binding_when_top_level_head_absent() -> None:
    # Empty top-level head forces the branch_bindings scan (lines 258-263). A non-dict
    # entry is skipped via `continue` (259-260); a non-matching dict falls through the
    # branch check (261 False); the matching branch binding returns its head (261-262).
    status_payload = {
        "head": "",
        "branch_bindings": [
            "not-a-dict-entry",
            {"branch": "other/lane", "head": "wronghead000000"},
            {"branch": "work/demo", "head": "deadbeefcafe12"},
        ],
    }

    assert _current_head(status_payload, branch="work/demo") == "deadbeefcafe12"


def test_next_actions_work_lane_without_closeout_support_binds_claim() -> None:
    # Clean work_lane, no gaps, closeout NOT supported: the closeout-supported elif
    # (line 333) is skipped and the bare work_lane branch (line 339-340) fires.
    actions = _next_actions(
        {
            "role": "work_lane",
            "dirty": False,
            "gaps": [],
            "closeout": {"supported": False},
            "report_payload": None,
            "advisory_next_actions": [],
        }
    )

    assert actions == ["ethos lane bind-claim --claim-id <claim> --apply --json"]


def test_next_actions_candidate_role_lands_with_closeout() -> None:
    # Clean candidate with no gaps reaches the candidate branch (line 343-344).
    actions = _next_actions(
        {
            "role": "candidate",
            "dirty": False,
            "gaps": [],
            "closeout": {},
            "report_payload": None,
            "advisory_next_actions": [],
        }
    )

    assert actions == ["ethos land --closeout --json"]


def test_format_policy_reports_gap_when_rules_toml_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # tmp_path has no .ethos/rules.toml, so format_policy() takes the else arm
    # (lines 399-400): policy = {} and a format_policy_missing gap is raised.
    monkeypatch.setattr(quality, "resolve_root", lambda root: tmp_path)
    emitted: list[EthosResult] = []
    monkeypatch.setattr(
        quality, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )
    quality.format_policy(root=tmp_path, json_output=True)
    result = emitted[-1]
    assert result.required_gaps == ("format_policy_missing:.ethos/rules.toml",)
    assert result.ok is False
    assert result.data["formats"] == {}
    assert result.data["artifacts"] == {}
    assert result.data["determinism"] == {}
    assert result.data["standards"] == {}


def test_projection_drift_reports_missing_expected_digests(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Empty registry meta -> both expected-digest strings are '', so the
    # `if not expected_registry_digest` (line 440) and
    # `if not expected_generator_digest` (line 444) missing-branches fire.
    monkeypatch.setattr(quality, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(quality, "_sha256_file", lambda path: "sha256:actual")
    monkeypatch.setattr(
        quality,
        "playbooks_report",
        lambda root, *, mode="v2-strict": {
            "registry": {"meta": {}, "digest": "sha256:reg-actual"},
            "required_gaps": [],
        },
    )
    emitted: list[EthosResult] = []
    monkeypatch.setattr(
        quality, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )
    quality.projection_drift(root=tmp_path, json_output=True)
    result = emitted[-1]
    assert "skill_registry_expected_digest_missing" in result.required_gaps
    assert "projection_generator_expected_digest_missing" in result.required_gaps
    assert result.ok is False


def test_projection_drift_reports_digest_mismatches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Expected digests present but differ from actual -> the elif mismatch
    # branches fire: registry mismatch (line 442) and generator mismatch (line 448).
    monkeypatch.setattr(quality, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(quality, "_sha256_file", lambda path: "sha256:gen-actual")
    monkeypatch.setattr(
        quality,
        "playbooks_report",
        lambda root, *, mode="v2-strict": {
            "registry": {
                "meta": {
                    "expected_registry_digest": "sha256:reg-expected",
                    "expected_generator_digest": "sha256:gen-expected",
                },
                "digest": "sha256:reg-actual",
            },
            "required_gaps": [],
        },
    )
    emitted: list[EthosResult] = []
    monkeypatch.setattr(
        quality, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )
    quality.projection_drift(root=tmp_path, json_output=True)
    result = emitted[-1]
    assert "skill_registry_digest_mismatch" in result.required_gaps
    assert "projection_generator_digest_mismatch" in result.required_gaps
    assert result.ok is False
