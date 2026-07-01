from __future__ import annotations

from pathlib import Path

from ethos_adapters import openspec_native


def test_openspec_lifecycle_requires_active_claim_binding(tmp_path: Path, monkeypatch) -> None:
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

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        if args == ("doctor", "--json"):
            payload = {"root": {"healthy": True}}
        elif args == ("list", "--json"):
            payload = {"changes": [{"name": "sample-change", "status": "in-progress"}]}
        elif args == ("status", "--change", "sample-change", "--json"):
            payload = {"isComplete": True, "schemaName": "spec-driven"}
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

    monkeypatch.setattr(openspec_native, "_openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_native, "_run_json", fake_run_json)

    report = openspec_native.openspec_governance_report(
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

    monkeypatch.setattr(openspec_native, "_openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_native, "_run_json", fake_run_json)

    report = openspec_native.completed_active_changes_report(root)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["completed_changes"] == ["done-change"]
    assert report["required_gaps"] == ["openspec_completed_change_unarchived:done-change"]
    assert calls == [("list", "--json")]


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

    monkeypatch.setattr(openspec_native, "_openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec_native, "_run_json", fake_run_json)

    first = openspec_native.openspec_governance_report(root)
    second = openspec_native.openspec_governance_report(root)

    assert first == second
    assert calls == [
        ("doctor", "--json"),
        ("list", "--json"),
        ("validate", "--all", "--strict", "--json"),
    ]
