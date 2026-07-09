from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_quality_no_compat_command_reports_clean_current_product() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ethos.cli",
            "quality",
            "no-compat",
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["ok"] is True
    assert payload["state"] == "clean"
    assert payload["summary"]["finding_count"] == 0


def test_quality_no_compat_command_reports_blocked_custom_root(tmp_path: Path) -> None:
    sample = tmp_path / "packages/ethos/src/ethos/sample/core.py"
    sample.parent.mkdir(parents=True)
    sample.write_text("def legacy_wrapper():\n    return 1\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ethos.cli",
            "quality",
            "no-compat",
            "--root",
            str(tmp_path),
            "--json",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["summary"] == {
        "finding_count": 1,
        "scanned_path_count": 1,
        "source_roots": ["packages/ethos/src", "packages/ethos-core/src"],
    }
    assert payload["required_gaps"] == [
        "no_compat_residue:forbidden_identifier:"
        "packages/ethos/src/ethos/sample/core.py:1:legacy_wrapper"
    ]


def test_quality_no_compat_function_emits_policy_report(monkeypatch, tmp_path: Path) -> None:
    from ethos.surface.cli.quality.cutover import core

    sample = tmp_path / "packages/ethos/src/ethos/sample/core.py"
    sample.parent.mkdir(parents=True)
    sample.write_text("def legacy_wrapper():\n    return 1\n", encoding="utf-8")
    emitted = []

    def fake_resolve_root(_root: Path) -> Path:
        return tmp_path

    def fake_emit(result: object, *, json_output: bool = False) -> None:
        assert json_output is True
        emitted.append(result)

    monkeypatch.setattr(core, "resolve_root", fake_resolve_root)
    monkeypatch.setattr(core, "emit", fake_emit)

    core.no_compat(root=tmp_path, json_output=True)

    assert len(emitted) == 1
    result = emitted[0]
    assert result.command == "quality no-compat"
    assert result.ok is False
    assert result.state == "blocked"
    assert result.summary == {
        "finding_count": 1,
        "scanned_path_count": 1,
        "source_roots": ["packages/ethos/src", "packages/ethos-core/src"],
    }
    assert result.required_gaps == (
        "no_compat_residue:forbidden_identifier:"
        "packages/ethos/src/ethos/sample/core.py:1:legacy_wrapper",
    )
