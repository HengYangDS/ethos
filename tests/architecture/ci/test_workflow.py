"""Native workflow checks preserve Actions meaning and finite shell input."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

import tools.ci.ci_projection as owner
from tests.support.architecture import isolated_path
from tests.support.architecture import write_reference_source

ROOT = owner.ROOT


@pytest.mark.parametrize("fault", ["none", "syntax", "missing-lock", "version-drift"])
def test_workflow_gate_uses_locked_native_tool_without_ambient_fallback(
    tmp_path, monkeypatch, fault
):
    """Run the real gate over a tiny workflow with a hostile ambient actionlint."""
    for path in (".config/mise/config.toml", ".config/mise/mise.lock"):
        write_reference_source(tmp_path, path, (ROOT / path).read_text())
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "name: check\non: push\njobs:\n  check:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n"
    )
    if fault == "syntax":
        workflow.write_text("on: push\njobs: [\n")
    elif fault == "missing-lock":
        (tmp_path / ".config/mise/mise.lock").unlink()
    elif fault == "version-drift":
        config = tmp_path / ".config/mise/config.toml"
        config.write_text(config.read_text().replace('"1.7.12"', '"0.0.0"'))
    trap = isolated_path(tmp_path, {"actionlint": "#!/bin/sh\ntouch AMBIENT_EXECUTED\nexit 0\n"})
    monkeypatch.setenv("PATH", trap["PATH"] + os.pathsep + os.environ["PATH"])
    before = workflow.read_bytes()
    assert (owner.check_workflow(tmp_path) == 0) is (fault == "none")
    assert workflow.read_bytes() == before
    assert not (tmp_path / "AMBIENT_EXECUTED").exists()


@pytest.mark.parametrize("fault", ["none", "shell", "expression"])
def test_native_workflow_gate_preserves_large_input_and_semantic_rejections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """A real native workload reaches EOF while Actions and shell faults remain adverse."""
    for relative in (".config/mise/config.toml", ".config/mise/mise.lock"):
        write_reference_source(tmp_path, relative, (ROOT / relative).read_text())
    script = "printf '%s\\n' 'native-input'\n" * 5000
    if fault == "shell":
        script += "if then\n"
    elif fault == "expression":
        script += "echo '${{ missing_context.value }}'\n"
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        yaml.safe_dump(
            {
                "name": "native",
                "on": "push",
                "jobs": {"native": {"runs-on": "ubuntu-latest", "steps": [{"run": script}]}},
            }
        )
    )
    before = workflow.read_bytes()
    native_run = owner.run_command

    def bounded_run(root: Path, command: tuple[str, ...], **kwargs):
        # Bound a deadlocked child, not a loaded runner: shellcheck needs seconds for this input.
        kwargs["timeout"] = min(kwargs.get("timeout", 30), 30)
        return native_run(root, command, **kwargs)

    monkeypatch.setattr(owner, "run_command", bounded_run)
    assert (owner.check_workflow(tmp_path) == 0) is (fault == "none")
    assert workflow.read_bytes() == before


@pytest.mark.parametrize(
    ("workflow_shell", "job_shell", "step_shell", "runner", "expected"),
    [
        ("", "", "", "ubuntu-latest", "bash"),
        ("", "", "", "windows-latest", "pwsh"),
        ("sh", "", "", "windows-latest", "sh"),
        ("sh", "bash", "", "windows-latest", "bash"),
        ("bash", "sh", "bash {0}", "ubuntu-latest", "bash"),
    ],
)
def test_workflow_shell_projection_preserves_native_precedence(
    tmp_path: Path,
    workflow_shell: str,
    job_shell: str,
    step_shell: str,
    runner: str,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Platform defaults do not override a step, job or workflow shell declaration."""
    workflow = {
        "defaults": {"run": {"shell": workflow_shell}},
        "jobs": {
            "build": {
                "runs-on": runner,
                "defaults": {"run": {"shell": job_shell}},
                "steps": [{"shell": step_shell, "run": "echo '${{ '中文' }}'"}],
            }
        },
    }
    source = tmp_path / ".github/workflows/ci.yml"
    source.parent.mkdir(parents=True)
    source.write_text(yaml.safe_dump(workflow))
    monkeypatch.setattr(owner, "locked_tool", lambda *_args: Path("actionlint"))
    monkeypatch.setattr(owner.ProjectRuntime, "script", lambda *_args: "shellcheck")
    inputs = []

    def observe(_root: Path, command: tuple[str, ...], **kwargs):
        if command[0] == "shellcheck":
            inputs.append(kwargs["stdin"])
        return subprocess.CompletedProcess(
            command, 0, "[]" if command[0] == "shellcheck" else "", ""
        )

    monkeypatch.setattr(owner, "run_command", observe)
    assert owner.check_workflow(tmp_path) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["shell"] == expected
    if expected in {"bash", "sh"}:
        assert len(inputs) == 1
        assert "${{" not in inputs[0]
        assert "echo '" in inputs[0]
        assert "_" * len("${{ '中文' }}".encode()) in inputs[0]
    else:
        assert not inputs
        assert report["state"] == "not_applicable"


@pytest.mark.parametrize("fault", ["warning", "malformed", "timeout", "source-drift"])
def test_workflow_native_failure_cannot_become_a_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """Preserve adverse native diagnostics, deadline failures and exact-source loss."""
    workflow = tmp_path / ".github/workflows/ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "on: push\njobs:\n  check:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n"
    )
    monkeypatch.setattr(owner, "locked_tool", lambda *_args: Path("actionlint"))
    monkeypatch.setattr(owner.ProjectRuntime, "script", lambda *_args: "shellcheck")

    def observe(_root: Path, command: tuple[str, ...], **kwargs):
        if command[0] == "actionlint":
            if fault == "source-drift":
                workflow.write_text(workflow.read_text() + "# peer\n")
            return subprocess.CompletedProcess(command, 0, "", "")
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], "partial", "owned timeout")
        stdout = "{}" if fault == "malformed" else json.dumps([{"level": "warning", "code": 2086}])
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(owner, "run_command", observe)
    assert owner.check_workflow(tmp_path) == 1
