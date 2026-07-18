from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.surface.cli.results import tool as tool_results

if TYPE_CHECKING:
    from pathlib import Path


def test_emit_quality_tool_result_builds_standard_result(monkeypatch, tmp_path: Path) -> None:
    emitted = []

    def fake_report(**kwargs):
        return {"ok": False, "required_gaps": ["tool_gap"], "state": "failed", **kwargs}

    monkeypatch.setattr(tool_results, "quality_tool_report", fake_report)

    def capture_emit(result, *, json_output=False, enforce=True) -> None:
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(tool_results, "emit", capture_emit)

    tool_results.emit_quality_tool_result(
        root=tmp_path,
        gate_id="demo-gate",
        tool="demo-tool",
        command=["demo", "--check"],
        files=["a.py"],
        result_command="quality demo",
        json_output=True,
    )

    assert emitted == [
        {
            "schema_version": 1,
            "command": "quality demo",
            "ok": False,
            "state": "blocked",
            "summary": {},
            "diagnostics": [],
            "required_gaps": ["tool_gap"],
            "next_actions": [],
            "data": {
                "ok": False,
                "required_gaps": ["tool_gap"],
                "state": "failed",
                "root": tmp_path,
                "gate_id": "demo-gate",
                "tool": "demo-tool",
                "command": ["demo", "--check"],
                "files": ["a.py"],
            },
        }
    ]
