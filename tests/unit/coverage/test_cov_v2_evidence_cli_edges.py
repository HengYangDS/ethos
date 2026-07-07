# ruff: noqa: ARG005, TC002, TC003
"""Coverage-closure edge tests for the evidence/parity + surface CLI + playbooks cluster.

Second coverage pass (v2): each test drives one specific uncovered line in
- ethos.repository.evidence.parity (210, 233-244, 412)
- ethos.surface.cli.parity (117, 119)
- ethos.surface.cli.assistants (200-211)
- ethos.assistants.playbooks (85, 142, 190, 332, 334, 342, 384, 432, 478, 486)
"""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.shadow.core as shadow_core
from ethos.assistants import playbooks
from ethos.assistants.skills import portfolio
from ethos.repository.evidence import parity
from ethos.surface.cli import assistants as assistants_cli
from ethos.surface.cli import parity as parity_cli

# --------------------------------------------------------------------------- #
# ethos.repository.evidence.parity
# --------------------------------------------------------------------------- #


def test_shadow_identity_takes_dict_branch(tmp_path: Path) -> None:
    # shadow carries an `identity` dict, so _shadow_identity takes the dict branch
    # (line 210) rather than the default-empty fallback, threading each field through.
    shadow = {
        "ok": True,
        "state": "matched",
        "required_gaps": [],
        "accepted_summary": {"total_count": 1, "kind_counts": {}, "command_count": 1},
        "false_negative_count": 0,
        "identity": {
            "target_root": "/custom/root",
            "target_head": "th",
            "product_head": "ph",
            "changed_paths": ["packages/x"],
            "commands": ["ethos status --json"],
            "external_commands": ["ext"],
            "embedded_commands": ["emb"],
            "evidence_inputs": [{"path": "p", "kind": "k", "sha256": "s"}],
        },
    }

    evidence = parity.build_tracked_parity_evidence(
        adopter="demo",
        target=tmp_path,
        shadow=shadow,
        current_product_head="p1",
        current_target_head="t1",
        timeout_seconds=30,
    )

    identity = evidence["identity"]
    assert identity["target_root"] == "/custom/root"
    assert identity["target_head"] == "th"
    assert identity["product_head"] == "ph"
    assert identity["external_commands"] == ["ext"]
    assert identity["evidence_inputs"] == [{"path": "p", "kind": "k", "sha256": "s"}]


def test_identity_evidence_inputs_filters_and_handles_non_list() -> None:
    # Non-list -> line 234 `return []`.
    assert parity._identity_evidence_inputs(None) == []
    # List path -> 235-244: a non-dict item is skipped (238 continue), a complete
    # dict is kept (243), and a dict missing a field fails the guard (242 False).
    filtered = parity._identity_evidence_inputs(
        [
            "skip-non-dict",
            {"path": "p", "kind": "k", "sha256": "s"},
            {"path": "", "kind": "k", "sha256": "s"},
        ]
    )
    assert filtered == [{"path": "p", "kind": "k", "sha256": "s"}]


def test_shadow_parity_report_flags_target_mismatch(tmp_path: Path) -> None:
    # Evidence is built for `other`, so its recorded target differs from the
    # target_identity computed for the reported `tmp_path`, firing the mismatch gap
    # at line 412 and routing the report into the `invalid` branch.
    other = tmp_path / "other"
    other.mkdir()
    evidence = parity.build_tracked_parity_evidence(
        adopter="demo",
        target=other,
        shadow={"ok": True, "required_gaps": [], "accepted_summary": {"total_count": 1}},
        current_product_head="p1",
        current_target_head="t1",
        timeout_seconds=30,
    )
    parity.write_tracked_parity_evidence(root=tmp_path, adopter="demo", evidence=evidence)

    report = parity.shadow_parity_report(target=tmp_path, root=tmp_path, adopter="demo")

    assert report["state"] == "invalid"
    assert any(
        str(gap).startswith("shadow_parity_evidence_target_mismatch:demo")
        for gap in report["required_gaps"]
    )


# --------------------------------------------------------------------------- #
# ethos.surface.cli.parity
# --------------------------------------------------------------------------- #


def test_parity_shadow_write_evidence_requires_execute(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # write_evidence without execute -> line 117 gap; the planned (non-execute) report
    # runs for real against an empty tmp_path (no tracked evidence file).
    monkeypatch.setattr(parity_cli, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(parity_cli._gitio, "current_tracked_head", lambda root: "")
    monkeypatch.setattr(
        parity_cli._land, "acceptable_parity_product_heads", lambda repo, adopter: ()
    )
    monkeypatch.setattr(
        parity_cli._land, "acceptable_parity_target_heads", lambda repo, target, adopter: ()
    )
    emitted: list[object] = []
    monkeypatch.setattr(
        parity_cli, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )

    parity_cli.parity_shadow(
        target=tmp_path,
        adopter="demo",
        execute=False,
        write_evidence=True,
        json_output=True,
    )

    result = emitted[-1]
    assert "parity_evidence_write_requires_execute" in result.required_gaps


def test_parity_shadow_write_evidence_blocked_when_not_ok(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # execute=True but the shadow run reports ok!=True -> line 119 blocked gap.
    monkeypatch.setattr(parity_cli, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(
        shadow_core,
        "run_shadow_parity",
        lambda target, timeout_seconds, product_root: {
            "ok": False,
            "state": "mismatch",
            "required_gaps": [],
        },
    )
    emitted: list[object] = []
    monkeypatch.setattr(
        parity_cli, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )

    parity_cli.parity_shadow(
        target=tmp_path,
        adopter="demo",
        execute=True,
        write_evidence=True,
        json_output=True,
    )

    result = emitted[-1]
    assert "parity_evidence_write_blocked:demo" in result.required_gaps


# --------------------------------------------------------------------------- #
# ethos.surface.cli.assistants
# --------------------------------------------------------------------------- #


def test_assistants_context_eval_reports_missing_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Drives the whole assistants_context_eval body (200-211): smoke fixtures are
    # loaded, context_eval_report runs against an empty repo (no retrieval db), and the
    # missing-index gap is emitted.
    monkeypatch.setattr(assistants_cli, "resolve_root", lambda root: tmp_path)
    emitted: list[object] = []
    monkeypatch.setattr(
        assistants_cli, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )

    assistants_cli.assistants_context_eval(root=tmp_path, suite="smoke", json_output=True)

    result = emitted[-1]
    assert result.command == "assistants context-eval"
    assert result.ok is False
    assert "context_index_missing" in result.required_gaps


# --------------------------------------------------------------------------- #
# ethos.assistants.playbooks
# --------------------------------------------------------------------------- #


def test_playbooks_report_flags_missing_readme(tmp_path: Path) -> None:
    # skills_root exists but has no README.md -> line 85 required gap.
    (tmp_path / ".agents" / "skills").mkdir(parents=True)

    report = playbooks.playbooks_report(tmp_path)

    assert ".agents/skills/README.md" in report["required_gaps"]


def test_collect_playbook_records_flags_missing_file(tmp_path: Path) -> None:
    # A record with a valid (non-escaping) path whose file is absent -> the elif at
    # line 141 is True and line 142 appends skill_missing_file.
    skills_root = tmp_path / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    (skills_root / "activation.toml").write_text(
        "[meta]\nversion = 2\n\n"
        '[[skill]]\nid = "ghost-skill"\n'
        'path = ".agents/skills/ghost-skill/SKILL.md"\nsubject = "ghost"\n',
        encoding="utf-8",
    )

    report = playbooks.playbooks_report(tmp_path)

    assert "skill_missing_file:ghost-skill" in report["required_gaps"]


def test_transition_registry_skips_non_dict_skill(tmp_path: Path) -> None:
    # profile present + activation meta version < 2 -> transition adopter path, and a
    # non-dict `skill` entry hits the `continue` at line 190.
    skills_root = tmp_path / ".agents" / "skills"
    skills_root.mkdir(parents=True)
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'schema_version = 1\n[roots]\nagent_skills = ".agents/skills"\n',
        encoding="utf-8",
    )
    (skills_root / "activation.toml").write_text(
        'skill = ["not-a-dict"]\n\n[meta]\nversion = 1\n',
        encoding="utf-8",
    )

    report = playbooks.playbooks_report(tmp_path)

    assert report["skills"] == []


def test_strict_record_gaps_flags_lifecycle_path_globs_commands() -> None:
    # Empty lifecycle / path_globs / commands drive lines 332, 334, 342; the other
    # fields are populated so only those three gaps are raised.
    record = {
        "id": "s",
        "primary_subject": "subj",
        "operation": "op",
        "authority": "primary",
        "lifecycle": "",
        "activation": {"path_globs": []},
        "obligations": {"pre_reads": ["AGENTS.md"], "post_checks": ["ethos report --json"]},
        "package_manifest": "package.toml",
        "commands": [],
    }

    gaps = playbooks._strict_record_gaps(record)

    assert gaps == [
        "playbook_skill_missing_lifecycle:s",
        "playbook_skill_missing_path_globs:s",
        "playbook_skill_missing_commands:s",
    ]


def test_root_relative_returns_empty_for_absolute_path(tmp_path: Path) -> None:
    # An absolute candidate path -> is_absolute() True -> line 384 `return ""`.
    assert playbooks._root_relative(tmp_path, "/abs/escape/SKILL.md") == ""


def test_portfolio_coverage_skips_record_with_empty_id() -> None:
    # authority/lifecycle pass the first guard, but the empty id trips the guard at
    # line 431 and skips ownership registration via line 432.
    result = portfolio.portfolio_coverage(
        {},
        [{"authority": "primary", "lifecycle": "active", "primary_subject": "subj", "id": ""}],
    )

    assert result["owners"] == {}


def test_portfolio_design_flags_overloaded_package_and_overclaimed_token() -> None:
    # One package exceeds the file limit (line 478); one intent token is owned by more
    # than the allowed number of skills (line 486).
    records = [
        {
            "id": f"s{index}",
            "subjects": ["shared"],
            "primary_subject": "shared",
            "commands": [],
            "path_globs": [],
            "intent_tokens": ["shared"],
        }
        for index in range(3)
    ]
    package_reports = [
        {"id": "s0", "files": ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]},
        {"id": "s1", "files": []},
        {"id": "s2", "files": []},
    ]

    result = portfolio.portfolio_design(records, package_reports)

    gaps = result["required_gaps"]
    assert any(gap.startswith("skill_portfolio_package_overloaded:s0:7") for gap in gaps)
    assert any(gap.startswith("skill_portfolio_intent_token_overclaimed:shared:") for gap in gaps)
