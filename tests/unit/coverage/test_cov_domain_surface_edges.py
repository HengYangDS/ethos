# ruff: noqa: ARG005, TC001, TC002, TC003
"""Coverage-closure edge tests for the domain_surface cluster (100% no-exemption campaign)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.domain.land.core as land_core
import ethos.surface.cli.quality.core as quality

# ruff: noqa: ARG005, TC002
from ethos.assistants import projections
from ethos.domain.orient import orientation_packet
from ethos_core.result import EthosResult


def test_land_closeout_audit_root_non_dict_candidate(monkeypatch, tmp_path: Path) -> None:
    # decision.ok is truthy so the guard on line 53 passes, but workspace_status
    # yields a non-dict candidate, driving the isinstance guard to line 57's `return repo`.
    decision = SimpleNamespace(ok=True)
    monkeypatch.setattr(
        land_core,
        "workspace_status",
        lambda repo, **_kwargs: {"candidate": "not-a-dict"},
    )
    assert land_core.closeout_audit_root(tmp_path, decision) == tmp_path


def test_runner_source_root_fallback_without_source_tree(tmp_path: Path) -> None:
    # No ancestor of this synthetic path has pyproject.toml + packages/ethos/src/ethos/__init__.py,
    # so the loop finds no match and falls through to line 69's `return module_path.parent`.
    module_path = tmp_path / "runner" / "ethos.py"
    assert land_core.runner_source_root(module_path) == tmp_path / "runner"


def _orientation(role: str, **overrides: object) -> dict[str, object]:
    return orientation_packet(
        status_payload={
            "root": "/repo",
            "branch": "work/demo",
            "role": role,
            "dirty": False,
            "changed_paths": [],
            "closeout_support": {"supported": False},
            "coordination": {},
            "foreign_work_lanes": [],
            **overrides,
        }
    )


def test_current_head_falls_back_to_matching_branch_binding_when_top_level_head_absent() -> None:
    packet = _orientation(
        "work_lane",
        head="",
        branch_bindings=[
            "not-a-dict-entry",
            {"branch": "other/lane", "head": "wronghead000000"},
            {"branch": "work/demo", "head": "deadbeefcafe12"},
        ],
    )

    assert packet["where"]["head"] == "deadbeefcafe12"


def test_next_actions_work_lane_withoutcloseout_support_binds_claim() -> None:
    assert _orientation("work_lane")["next_actions"] == [
        "ethos lane bind-claim --claim-id <claim> --apply --json"
    ]


def test_next_actions_candidate_role_lands_with_closeout() -> None:
    assert _orientation("candidate")["next_actions"] == ["ethos land --closeout --json"]


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
    # Empty registry meta -> both expected-digest strings are '', so the missing
    # branches fire in the assistant projection report owner.
    monkeypatch.setattr(projections, "_sha256_file", lambda path: "sha256:actual")
    monkeypatch.setattr(
        projections,
        "playbooks_report",
        lambda root, *, mode="v2-strict": {
            "registry": {"meta": {}, "digest": "sha256:reg-actual"},
            "required_gaps": [],
        },
    )
    result = projections.projection_drift_report(tmp_path)

    assert "skill_registry_expected_digest_missing" in result["required_gaps"]
    assert "projection_generator_expected_digest_missing" in result["required_gaps"]
    assert result["ok"] is False


def test_projection_drift_reports_digest_mismatches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Expected digests present but differ from actual -> the mismatch branches fire.
    monkeypatch.setattr(projections, "_sha256_file", lambda path: "sha256:gen-actual")
    monkeypatch.setattr(
        projections,
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
    result = projections.projection_drift_report(tmp_path)

    assert "skill_registry_digest_mismatch" in result["required_gaps"]
    assert "projection_generator_digest_mismatch" in result["required_gaps"]
    assert result["ok"] is False
