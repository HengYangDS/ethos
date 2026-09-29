"""Native type diagnostics cannot become green through prose or a zero exit alone."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.gates.ty as ty


def test_native_ty_scope_rejects_errors_in_each_owned_carrier(tmp_path: Path) -> None:
    """Native Ty selection, not a copied path filter, covers the declared floor."""
    root = Path(__file__).resolve().parents[4]
    config = tmp_path / "ty.toml"
    config.write_bytes((root / ".config/checks/ty/ty.toml").read_bytes())
    targets = {
        "src/ethos/typing_probe.py",
        "tools/ci/typing_probe.py",
        "tests/support/typing_probe.py",
        "tests/architecture/typing_probe.py",
        "noxfile.py",
    }
    for target in targets:
        source = tmp_path / target
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('result: int = "wrong"\n', encoding="utf-8")

    completed = subprocess.run(
        (
            sys.executable,
            "-m",
            "ty",
            "check",
            "--project",
            str(tmp_path),
            "--config-file",
            str(config),
            "--output-format",
            "gitlab",
        ),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    diagnostics = json.loads(completed.stdout)
    found = {str(Path(item["location"]["path"]).relative_to(tmp_path)) for item in diagnostics}
    assert found == targets
    assert {item["check_name"] for item in diagnostics} == {"invalid-assignment"}


def test_ty_gate_requires_native_config(tmp_path: Path) -> None:
    assert ty.ty_gate_report(tmp_path) == {
        "verdict": "block",
        "state": "blocked",
        "required_gaps": ["ty_config_missing"],
        "analysis": {},
    }


@pytest.mark.parametrize(
    ("exit_code", "output", "gap", "count"),
    [
        (None, OSError("unavailable"), "ty_execution_failed:launch", None),
        (None, subprocess.TimeoutExpired("ty", 120), "ty_execution_failed:timeout", None),
        (2, "[]", "ty_execution_failed:2", 0),
        (0, "All checks passed", "ty_execution_failed:0", None),
        (0, '[{"description":"broken"}]', "ty_execution_failed:0", None),
        (0, '["not a diagnostic"]', "ty_execution_failed:0", None),
        (0, '[{"description":"broken","severity":[]}]', "ty_execution_failed:0", None),
        (1, '[{"description":"finding","severity":"major"}]', "ty_zero_tolerance_violation:1", 1),
        (1, '[{"description":"finding","severity":"minor"}]', "ty_zero_tolerance_violation:1", 1),
        (0, '[{"description":"finding","severity":"minor"}]', "ty_zero_tolerance_violation:1", 1),
        (0, "[]", "", 0),
    ],
)
def test_ty_gate_classifies_tool_and_diagnostic_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code,
    output,
    gap,
    count,
) -> None:
    """Native payload, process status and failure stage have independent expectations."""
    config = tmp_path / ".config/checks/ty/ty.toml"
    config.parent.mkdir(parents=True)
    config.write_text('[src]\ninclude = ["src"]\n', encoding="utf-8")

    def run(root, command, **kwargs):
        assert root == tmp_path
        assert "--error-on-warning" in command
        assert command[command.index("--output-format") + 1] == "gitlab"
        assert command[command.index("--config-file") + 1] == str(config)
        assert command[command.index("--project") + 1] == str(tmp_path)
        assert "--frozen" in command
        assert "--offline" in command
        assert kwargs["timeout"] == 120
        if isinstance(output, Exception):
            raise output
        return subprocess.CompletedProcess(command, exit_code, output, "informational output")

    monkeypatch.setattr(ty, "run_command", run)
    report = ty.ty_gate_report(tmp_path)
    assert report["required_gaps"] == ([gap] if gap else [])
    package = report["analysis"]
    state = "tool_error" if "execution_failed" in gap else "diagnostics" if gap else "clean"
    assert (package["state"], package["count"]) == (state, count)
    if isinstance(output, OSError):
        assert package["diagnostic_excerpt"] == ["OSError: unavailable"]
