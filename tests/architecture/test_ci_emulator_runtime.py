"""Keep emulator absence, timeout and partial logs distinct from hosted success."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

import tools.ci.ci_projection as projection
import tools.ci.ci_templates as ci
from tests.support.architecture import write_reference_source
from tools.ci.ci_projection import emulator_declaration
from tools.ci.ci_projection import provider_entry


@pytest.mark.parametrize("available", [False, True])
@pytest.mark.parametrize("relative", [False, True], ids=["absolute-path", "child-relative-path"])
def test_emulator_uses_exact_child_environment_locator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, available: bool, relative: bool
) -> None:
    """Execution selects the child PATH, not a locator from the parent environment."""
    native = Path(sys.executable)
    absent = tmp_path / "empty"
    absent.mkdir()
    child_path = native.parent if available else absent
    parent_path = absent if available else native.parent
    monkeypatch.setenv("PATH", str(parent_path))
    selected_path = os.path.relpath(child_path, tmp_path) if relative else str(child_path)
    environment = dict(os.environ, PATH=selected_path)
    log = tmp_path / "emulator.log"
    result = ci.run_command(
        [native.name, "-c", "import sys; print(sys.executable)"],
        cwd=tmp_path,
        env=environment,
        timeout_seconds=10,
        log_path=log,
        dry_run=False,
    )
    assert result["returncode"] == (0 if available else 127), result
    if available:
        assert Path(result["stdout"].strip()).resolve() == native.resolve()
    else:
        assert not log.exists()


def test_emulator_timeout_preserves_partial_log_and_blocks(monkeypatch, tmp_path: Path) -> None:
    process = Mock(pid=42)
    process.wait.side_effect = [ci.subprocess.TimeoutExpired(["emulator"], 1), -15]
    monkeypatch.setattr(ci.shutil, "which", lambda *_args, **_kwargs: "/bin/emulator")
    monkeypatch.setattr(ci.subprocess, "Popen", lambda *_args, **_kwargs: process)
    result = ci.run_command(
        ["emulator"],
        cwd=tmp_path,
        env={},
        timeout_seconds=1,
        log_path=tmp_path / "emulator.log",
        dry_run=False,
    )
    assert result["returncode"] == 124
    assert result["timed_out"] is True
    assert "timed out" in result["stderr"]


def test_gitlab_emulator_image_is_derived_from_its_ci_projection(
    monkeypatch, tmp_path: Path
) -> None:
    """The local emulator consumes the hosted image, not a second editable pin."""
    entry = provider_entry("gitlab")
    assert "emulator_image" not in entry
    image = "ghcr.io/example/supply@sha256:" + "0" * 64
    path = entry["projection"]
    write_reference_source(
        tmp_path, path, json.dumps({entry["emulator_job"]: {"image": {"name": image}}})
    )
    monkeypatch.setattr(projection, "ROOT", tmp_path)
    assert emulator_declaration(entry)["emulator_image"] == image
    write_reference_source(tmp_path, path, json.dumps({entry["emulator_job"]: {}}))
    with pytest.raises(SystemExit, match="CI emulator image unavailable"):
        emulator_declaration(entry)


@pytest.mark.parametrize("runner", ["macos-latest", "ubuntu-latest"])
def test_emulator_mapping_uses_selected_workflow(monkeypatch, tmp_path: Path, runner) -> None:
    entry = provider_entry("github")
    declaration = emulator_declaration(entry)
    workflow = {"jobs": {declaration["emulator_job"]: {"runs-on": runner}}}
    write_reference_source(tmp_path, ci.CONFIG_RELATIVE_PATH, "[compiler]\nsource='model.cue'")
    write_reference_source(tmp_path, "model.cue", "package ci")
    write_reference_source(tmp_path, entry["projection"], json.dumps(workflow))
    monkeypatch.setattr(ci, "ROOT", tmp_path)
    monkeypatch.setattr(ci.shutil, "which", lambda *_args, **_kwargs: None)
    output = tmp_path / "report.json"
    ci.emulator_evidence("github", mode="run", dry_run=True, allow_untracked=True, output=output)
    report = json.loads(output.read_text())
    assert report["command"][-2:] == ["--platform", f"{runner}={declaration['emulator_image']}"]
    assert report["hosted_github_status_claimed"] is False


@pytest.mark.parametrize(("mode", "expected"), [("doctor", 0), ("run", 127)])
def test_missing_emulator_is_observable_and_never_claims_hosted_success(
    monkeypatch, tmp_path: Path, mode: str, expected: int
) -> None:
    monkeypatch.setattr(ci.shutil, "which", lambda *_args, **_kwargs: None)
    output = tmp_path / f"{mode}.json"
    assert (
        ci.emulator_evidence(
            "gitlab", mode=mode, dry_run=False, allow_untracked=mode == "run", output=output
        )
        == expected
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["returncode"] == 127
    assert payload["hosted_gitlab_status_claimed"] is False
    assert payload["verdict"] == ("pass" if mode == "doctor" else "block")
