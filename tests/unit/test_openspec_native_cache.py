from __future__ import annotations

from pathlib import Path

from ethos_adapters import openspec_native


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

    first = openspec_native.openspec_self_governance_report(root)
    second = openspec_native.openspec_self_governance_report(root)

    assert first == second
    assert calls == [
        ("doctor", "--json"),
        ("list", "--json"),
        ("validate", "--all", "--strict", "--json"),
    ]
