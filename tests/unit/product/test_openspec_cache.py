from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.core as openspec_core
import ethos.adapters.openspec.lifecycle.core as openspec_lifecycle
import ethos.adapters.openspec.metadata.core as openspec_metadata_adapter

if TYPE_CHECKING:
    from pathlib import Path


def _lifecycle_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    change = root / "openspec" / "changes" / "sample-change"
    (root / "openspec" / "specs" / "ethos-repository").mkdir(parents=True)
    change.mkdir(parents=True)
    (root / "openspec" / "config.yaml").write_text("project: ethos\n", encoding="utf-8")
    (root / "openspec" / "specs" / "ethos-repository" / "spec.md").write_text(
        "# ETHOS Repository\n",
        encoding="utf-8",
    )
    for artifact in ("proposal.md", "design.md", "tasks.md"):
        (change / artifact).write_text("# artifact\n", encoding="utf-8")
    (change / "specs" / "ethos-repository").mkdir(parents=True)
    (change / "specs" / "ethos-repository" / "spec.md").write_text(
        "## ADDED Requirements\n",
        encoding="utf-8",
    )
    return root, change


def _openspec_base_command() -> tuple[str, ...]:
    return ("openspec",)


def _run_lifecycle_json(
    _root: Path,
    _base: tuple[str, ...],
    args: tuple[str, ...],
) -> dict[str, object]:
    payloads = {
        ("doctor", "--json"): {"root": {"healthy": True}},
        ("list", "--json"): {"changes": [{"name": "sample-change", "status": "in-progress"}]},
        ("status", "--change", "sample-change", "--json"): {
            "isComplete": True,
            "schemaName": "spec-driven",
        },
        ("validate", "--all", "--strict", "--json"): {
            "items": [],
            "summary": {"totals": {"failed": 0}},
        },
    }
    return {
        "command": ["openspec", *args],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "json": payloads.get(args, {}),
        "parse_error": "",
    }


def test_openspec_lifecycle_requires_active_claim_binding(tmp_path: Path, monkeypatch) -> None:
    root, _ = _lifecycle_root(tmp_path)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", _openspec_base_command)
    monkeypatch.setattr(openspec_cli, "run_json", _run_lifecycle_json)

    report = openspec_core.openspec_governance_report(
        root,
        change="sample-change",
        lifecycle=True,
    )

    assert report["ok"] is False
    assert "openspec_claim_binding_missing:sample-change" in report["required_gaps"]
    assert report["lifecycle"]["changes"][0]["carriers"] == {
        "proposal": True,
        "design": True,
        "tasks": True,
        "delta_specs": True,
        "claim_binding": False,
    }


def test_openspec_lifecycle_requires_product_protocol_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, change = _lifecycle_root(tmp_path)
    (change / "proposal.md").write_text(
        "## Why\nTest product protocol validation.\n\n## Capabilities\n- `unknown-capability`: subject=sample; reuse=borrow; change=modify\n",
        encoding="utf-8",
    )
    (root / "evidence" / "claims").mkdir(parents=True)
    (root / "evidence" / "claims" / "sample.toml").write_text(
        "\n".join(
            [
                "[claim]",
                'id = "sample"',
                'subject = "ethos:sample"',
                'state = "active"',
                'summary = "sample"',
                "",
                "[evidence]",
                'dated = "evidence/sample.md"',
                f'sha256 = "{"0" * 64}"',
                'tests = ["pytest"]',
                'evidence_ids = ["evidence:sample"]',
                'binding = "sample"',
                'verifier = "digest_only"',
                "",
                "[boundary]",
                'owner = "ethos-repository"',
                'scope = "sample"',
                "",
                "[carriers]",
                'openspec = "openspec/changes/sample-change"',
                'fallback = "sample"',
                'kill_signal = "sample"',
                "",
                "[promotion]",
                'targets = ["openspec/changes/sample-change"]',
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(openspec_cli, "openspec_base_command", _openspec_base_command)
    monkeypatch.setattr(openspec_cli, "run_json", _run_lifecycle_json)

    report = openspec_core.openspec_governance_report(
        root,
        change="sample-change",
        lifecycle=True,
    )

    assert report["ok"] is False
    assert "openspec_proposal_out_of_scope_missing:sample-change" in report["required_gaps"]
    assert (
        "openspec_proposal_capability_unknown:sample-change:unknown-capability"
        in report["required_gaps"]
    )
    assert (
        "openspec_capability_profile_missing:sample-change:unknown-capability"
        in report["required_gaps"]
    )
    assert (
        "openspec_proposal_metadata_missing:sample-change:unknown-capability:facet:lifecycle"
        in report["required_gaps"]
    )
    assert (
        "openspec_proposal_reuse_invalid:sample-change:unknown-capability:borrow"
        in report["required_gaps"]
    )


def test_completed_active_changes_report_blocks_complete_openspec_items(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec" / "changes" / "done-change").mkdir(parents=True)
    (root / "openspec" / "changes" / "active-change").mkdir(parents=True)

    calls: list[tuple[str, ...]] = []

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        calls.append(args)
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": {
                "changes": [
                    {"name": "done-change", "status": "complete"},
                    {"name": "active-change", "status": "in-progress"},
                ]
            },
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_cli, "run_json", fake_run_json)
    monkeypatch.setattr(
        openspec_metadata_adapter,
        "openspec_governance_report",
        lambda _root, **_kwargs: {"ok": True, "required_gaps": []},
        raising=False,
    )

    report = openspec_metadata_adapter.completed_active_changes_report(root)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["completed_changes"] == ["done-change"]
    assert report["required_gaps"] == ["openspec_completed_change_unarchived:done-change"]
    assert calls == [("list", "--json")]


def test_completed_active_changes_report_surfaces_active_archive_preflight(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)
    lifecycle = {
        "ok": False,
        "required_gaps": [
            "openspec_archive_preflight_failed:sample-change:archive_spec_update_failed"
        ],
    }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda *_args: {
            "command": ["openspec", "list", "--json"],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": {"changes": [{"name": "sample-change", "status": "in-progress"}]},
            "parse_error": "",
        },
    )
    monkeypatch.setattr(
        openspec_metadata_adapter,
        "openspec_governance_report",
        lambda _root, **_kwargs: lifecycle,
        raising=False,
    )

    report = openspec_metadata_adapter.completed_active_changes_report(root)

    assert report["ok"] is False
    assert report["active_lifecycle"] == lifecycle
    assert report["required_gaps"] == lifecycle["required_gaps"]


def test_completed_active_changes_report_blocks_invalid_archives(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    archive = root / "openspec" / "changes" / "archive" / "2026-07-02-sample-change"
    (archive / "specs" / "ethos-repository").mkdir(parents=True)
    (root / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    (archive / "proposal.md").write_text(
        "## Why\n\nArchive closeout needs product guards.\n\n## What Changes\n\n- Add guard.\n",
        encoding="utf-8",
    )
    (archive / "design.md").write_text(
        "## Context\n\nArchive closeout.\n\n## Design\n\nUse product guards.\n",
        encoding="utf-8",
    )
    (archive / "tasks.md").write_text("- [ ] Finish archive closeout.\n", encoding="utf-8")
    (archive / "specs" / "ethos-repository" / "spec.md").write_text(
        "## ADDED Requirements\n### Requirement: Archive Closeout\n#### Scenario: Archive is checked\n- **WHEN** closeout runs\n- **THEN** archive state is checked",
        encoding="utf-8",
    )

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": {"changes": []},
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_cli, "run_json", fake_run_json)
    monkeypatch.setattr(
        openspec_metadata_adapter,
        "openspec_governance_report",
        lambda _root, **_kwargs: {"ok": True, "required_gaps": []},
        raising=False,
    )

    report = openspec_metadata_adapter.completed_active_changes_report(root)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert "openspec_archive_metadata_missing:2026-07-02-sample-change" in (report["required_gaps"])
    assert "openspec_archive_tasks_incomplete:2026-07-02-sample-change" in (report["required_gaps"])
    assert report["archive_closeout"]["ok"] is False


def test_openspec_report_reuses_result_for_unchanged_workspace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    (root / "openspec" / "specs" / "ethos-core").mkdir(parents=True)
    (root / "openspec" / "config.yaml").write_text("project: ethos\n", encoding="utf-8")
    (root / "openspec" / "specs" / "ethos-core" / "spec.md").write_text(
        "# ETHOS Core\n",
        encoding="utf-8",
    )

    calls: list[tuple[str, ...]] = []

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        calls.append(args)
        if args == ("doctor", "--json"):
            payload = {"root": {"healthy": True}}
        elif args == ("list", "--json"):
            payload = {"changes": []}
        elif args == ("validate", "--all", "--strict", "--json"):
            payload = {"items": [], "summary": {"totals": {"failed": 0}}}
        else:
            payload = {}
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec_cli, "openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_cli, "run_json", fake_run_json)

    first = openspec_core.openspec_governance_report(root)
    second = openspec_core.openspec_governance_report(root)

    assert first == second
    assert calls == [
        ("doctor", "--json"),
        ("list", "--json"),
        ("validate", "--all", "--strict", "--json"),
    ]


def test_openspec_lifecycle_projects_archive_preflight(tmp_path: Path, monkeypatch) -> None:
    root, _change = _lifecycle_root(tmp_path)
    preflight = {
        "ok": False,
        "state": "blocked",
        "required_gaps": [
            "openspec_archive_preflight_failed:sample-change:archive_spec_update_failed"
        ],
        "diagnostics": [{"severity": "error", "code": "archive_spec_update_failed"}],
    }
    calls: list[tuple[Path, str]] = []

    monkeypatch.setattr(
        openspec_lifecycle,
        "active_claim_openspec_carriers",
        lambda _root: {"openspec/changes/sample-change"},
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "proposal_protocol_report",
        lambda _root, _change: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "openspec_archive_preflight_report",
        lambda current_root, current_change, **_kwargs: (
            calls.append((current_root, current_change)) or preflight
        ),
    )
    report = openspec_lifecycle.lifecycle_report(
        root,
        request=openspec_lifecycle.OpenSpecRequest(change=None, lifecycle=True),
        list_payload={"changes": [{"name": "sample-change"}]},
        base_command=("openspec",),
    )

    assert calls == [(root, "sample-change")]
    assert preflight["required_gaps"][0] in report["required_gaps"]
    assert report["changes"][0]["archive_preflight"] is preflight
