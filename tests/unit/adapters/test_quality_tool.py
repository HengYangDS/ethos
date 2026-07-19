from __future__ import annotations

import subprocess

from ethos.adapters.gates import tool as quality_tool


def test_quality_tool_report_skips_when_no_files(tmp_path):
    report = quality_tool.quality_tool_report(
        root=tmp_path,
        gate_id="markdown-links",
        tool="lychee",
        command=["lychee"],
        files=[],
    )

    assert report == {
        "ok": True,
        "id": "markdown-links",
        "tool": "lychee",
        "state": "skipped",
        "file_count": 0,
        "required_gaps": [],
    }


def test_quality_tool_report_blocks_missing_tool(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_tool.shutil, "which", lambda _tool: None)

    report = quality_tool.quality_tool_report(
        root=tmp_path,
        gate_id="shell-lint",
        tool="shellcheck",
        command=["shellcheck", "script.sh"],
        files=["script.sh"],
    )

    assert report["ok"] is False
    assert report["state"] == "missing_tool"
    assert report["required_gaps"] == ["quality_tool_missing:shellcheck"]


def test_quality_tool_report_passes_and_trims_output(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_tool.shutil, "which", lambda _tool: "/bin/tool")

    def fake_run(*args, **kwargs):
        assert kwargs["cwd"] == tmp_path
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(args[0], 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(quality_tool.subprocess, "run", fake_run)

    report = quality_tool.quality_tool_report(
        root=tmp_path,
        gate_id="config-quality",
        tool="taplo",
        command=["taplo", "check", "a.toml"],
        files=["a.toml"],
    )

    assert report["ok"] is True
    assert report["state"] == "passed"
    assert report["exit_code"] == 0
    assert report["stdout"] == "ok\n"
    assert report["required_gaps"] == []


def test_quality_tool_report_fails_with_gate_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(quality_tool.shutil, "which", lambda _tool: "/bin/tool")
    monkeypatch.setattr(
        quality_tool.subprocess,
        "run",
        lambda *args, **_kwargs: subprocess.CompletedProcess(args[0], 7, stdout="", stderr="bad"),
    )

    report = quality_tool.quality_tool_report(
        root=tmp_path,
        gate_id="config-quality",
        tool="yamllint",
        command=["yamllint", "bad.yml"],
        files=["bad.yml"],
    )

    assert report["ok"] is False
    assert report["state"] == "failed"
    assert report["exit_code"] == 7
    assert report["stderr"] == "bad"
    assert report["required_gaps"] == ["quality_gate_failed:config-quality"]
