"""Runtime contracts for local hosted-provider emulation."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_CONFIG = ROOT / ".config/checks/ci/templates.toml"


def _projection_entries() -> list[dict[str, object]]:
    entries = tomllib.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))["projection"]
    assert isinstance(entries, list)
    return entries


def _providers() -> dict[str, dict[str, object]]:
    return {str(entry["provider"]): entry for entry in _projection_entries()}


GITHUB_EMULATOR = {
    "provider": "github",
    "projection": ".github/workflows/ci.yml",
    "template": ".config/ci/templates/hosted/github-actions.yml",
    "emulator_tool": "act",
    "emulator_event": "workflow_dispatch",
    "emulator_job": "quality",
    "emulator_image": "example.invalid/runner@sha256:" + "1" * 64,
    "emulator_timeout_seconds": 1,
}


def _load_ci_templates_module():
    spec = importlib.util.spec_from_file_location(
        "ethos_test_ci_templates_runtime", ROOT / "tools/ci/ci_templates.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_emulator_run_persists_a_bounded_log_and_timeout_verdict(
    monkeypatch, tmp_path: Path
) -> None:
    """A timed-out emulator returns evidence and keeps its diagnostic log."""
    ci = _load_ci_templates_module()
    entry = GITHUB_EMULATOR
    summary = {
        "branch": "work/example",
        "head": "expected-head",
        "dirty": False,
        "status_short": "",
        "changed_scope": {
            "staged_paths": [],
            "unstaged_paths": [],
            "tracked_changed_paths": [],
            "untracked_count": 0,
            "untracked_preview": [],
            "untracked_preview_limit": 12,
        },
    }

    def materialize(**kwargs):
        source = kwargs["state_dir"] / "source"
        source.mkdir()
        return {"source_dir": str(source)}

    def time_out(*_args, **kwargs):
        log_path = kwargs["log_path"]
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("partial emulator output\n", encoding="utf-8")
        return {
            "returncode": 124,
            "ok": False,
            "stdout": "partial emulator output\n",
            "stderr": "emulator timed out after 1 seconds",
            "timed_out": True,
            "log_path": str(log_path),
        }

    monkeypatch.setattr(ci, "ROOT", tmp_path)
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    monkeypatch.setattr(ci.shutil, "which", lambda _: "/usr/local/bin/act")
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(ci, "_git_summary", lambda: summary)
    monkeypatch.setattr(ci, "materialize_emulator_source", materialize)
    monkeypatch.setattr(ci, "_run_command", time_out)
    output = tmp_path / "evidence" / "github-run.json"

    assert (
        ci.emulator_evidence(
            "github", mode="run", dry_run=False, allow_untracked=True, output=output
        )
        == 124
    )
    payload = json.loads(output.read_text())
    log_path = Path(payload["log_path"])
    assert payload["verdict"] == "block"
    assert payload["timed_out"] is True
    assert payload["timeout_seconds"] == 1
    assert log_path.is_file()
    assert log_path.read_text(encoding="utf-8") == "partial emulator output\n"


def test_emulator_materialization_preserves_branch_identity(tmp_path: Path) -> None:
    """A materialized checkout remains an on-branch Git repository for hosted gates."""
    ci = _load_ci_templates_module()
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(["git", "init", "--quiet", source], check=True)
    subprocess.run(["git", "-C", source, "checkout", "--quiet", "-b", "work/example"], check=True)
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", source, "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", source, "commit", "--quiet", "-m", "test"], check=True)
    expected_head = subprocess.run(
        ["git", "-C", source, "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    materialization = ci.materialize_emulator_source(
        source_root=source,
        state_dir=tmp_path / "state",
        expected_head=expected_head,
        expected_branch="work/example",
    )
    checkout = Path(materialization["source_dir"])

    assert materialization["source_branch"] == "work/example"
    assert materialization["source_branch_matches_expected"] is True
    assert (
        subprocess.run(
            ["git", "-C", checkout, "symbolic-ref", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "work/example"
    )


@pytest.mark.parametrize(
    ("mode", "expected_code", "output"), [("doctor", 0, None), ("run", 127, "gitlab-run.json")]
)
def test_local_emulator_missing_optional_tool(
    monkeypatch, tmp_path: Path, mode: str, expected_code: int, output: str | None
) -> None:
    ci = _load_ci_templates_module()
    monkeypatch.setattr(ci.shutil, "which", lambda _: None)
    destination = None if output is None else tmp_path / output
    assert (
        ci.emulator_evidence(
            "gitlab", mode=mode, dry_run=False, allow_untracked=mode == "run", output=destination
        )
        == expected_code
    )
    payload = json.loads(
        (ROOT / "build/evidence/local-ci/gitlab/doctor.json").read_text()
        if output is None
        else destination.read_text()
    )
    assert payload["tool_available"] is False
    assert payload["returncode"] == 127
    assert payload["stderr"] == "tool not found"
    if mode == "doctor":
        assert payload["verdict"] == "pass"
        assert payload["hosted_gitlab_status_claimed"] is False
    else:
        assert payload["verdict"] == "block"
        assert payload["materialization"] == {
            "issue": "",
            "mode_allows_untracked": False,
            "normal_run_refuses_untracked_by_default": True,
            "untracked_allowed": True,
            "untracked_policy": "refuse_before_emulator_run",
        }


def test_local_emulator_run_executes_a_selected_formal_provider_job(
    monkeypatch, tmp_path: Path
) -> None:
    ci, commands, roots, states = _load_ci_templates_module(), [], [], []
    monkeypatch.setattr(
        ci.shutil,
        "which",
        lambda tool: "/usr/local/bin/emulator" if tool in {"act", "gitlab-ci-local"} else None,
    )
    monkeypatch.setattr(ci, "_tool_version", lambda tool: f"{tool} 1.0")

    def materialize(**kwargs):
        state_dir = kwargs["state_dir"]
        states.append(state_dir)
        (state_dir / "source").mkdir(parents=True)
        return {"source_dir": str(state_dir / "source")}

    monkeypatch.setattr(ci, "materialize_emulator_source", materialize)

    def run_command(command, **kwargs):
        commands.append(command)
        roots.append(kwargs["cwd"])
        if command[0] == "gitlab-ci-local":
            state_dir = kwargs["cwd"] / command[command.index("--state-dir") + 1]
            assert state_dir.is_dir()
            assert (state_dir / "builds").is_dir()
        return {
            "returncode": 0,
            "ok": True,
            "stdout": "Job succeeded" if command[0] == "act" else "PASS ethos:carrier-quality",
            "stderr": "",
        }

    monkeypatch.setattr(ci, "_run_command", run_command)
    github_image = (
        "ghcr.io/catthehacker/ubuntu@sha256:"
        "148374205122af210a8ca475111dd1a2934a10bbeea39b53850041517dccc570"
    )
    expected_github = [
        "act",
        "workflow_dispatch",
        "-W",
        ".github/workflows/ci.yml",
        "-j",
        "quality",
        "--bind",
        "--platform",
        f"self-hosted={github_image}",
    ]
    images = {
        "github": github_image,
        "gitlab": (
            "ghcr.io/astral-sh/uv:0.12.2-python3.14-trixie-slim@sha256:"
            "d6e6a4de8d48bb4e64bcc2e2bd1e2291fb00ee4fd07a5dcfdc4c621afddcfe75"
        ),
    }
    providers = _providers()
    providers["github"] = providers["github"] | {"emulator_image": github_image}
    monkeypatch.setattr(ci, "_provider_entry", lambda provider: providers[provider])
    for provider in ("github", "gitlab"):
        output = tmp_path / f"{provider}.json"
        assert (
            ci.emulator_evidence(
                provider, mode="run", dry_run=False, allow_untracked=True, output=output
            )
            == 0
        )
        payload = json.loads(output.read_text())
        assert payload["execution"] == {
            "formal_workflow": ".github/workflows/ci.yml"
            if provider == "github"
            else ".gitlab-ci.yml",
            "mode": "selected_job_execution",
            "selected_job": "quality" if provider == "github" else "ethos:carrier-quality",
            "executed": True,
        }
        assert payload["execution_environment"] == {
            "declared_image": images[provider],
            "image_digest": images[provider].partition("@sha256:")[2],
            "image_digest_status": "declaration_bound",
            "tool_version": f"{commands[-1][0]} 1.0",
        }
    assert commands[0] == expected_github
    assert commands[1] == [
        "gitlab-ci-local",
        "--cwd",
        ".",
        "--file",
        ".gitlab-ci.yml",
        "--state-dir",
        os.path.relpath(states[1] / "state", states[1] / "source"),
        "ethos:carrier-quality",
    ]
    assert roots == [states[0] / "source", states[1] / "source"]
    assert all(not state.is_relative_to(ROOT) for state in states)
    assert all(not state.exists() for state in states)


@pytest.mark.parametrize(
    "stdout",
    [
        "Skipping unsupported platform -- Try running with -P self-hosted=...",
        "",
    ],
)
def test_github_emulator_rejects_a_zero_exit_run_without_executed_steps(
    monkeypatch, tmp_path: Path, stdout: str
) -> None:
    ci = _load_ci_templates_module()
    monkeypatch.setattr(ci.shutil, "which", lambda _: "/usr/local/bin/act")
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(
        ci,
        "materialize_emulator_source",
        lambda **kwargs: {"source_dir": str(kwargs["state_dir"] / "source")},
    )
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda _command, **_: {"returncode": 0, "ok": True, "stdout": stdout, "stderr": ""},
    )
    output = tmp_path / "github-run.json"

    assert (
        ci.emulator_evidence(
            "github", mode="run", dry_run=False, allow_untracked=True, output=output
        )
        == 1
    )
    payload = json.loads(output.read_text())
    assert payload["verdict"] == "block"
    assert payload["execution"]["executed"] is False


@pytest.mark.parametrize(
    ("stdout", "expected_code", "warnings"),
    [
        ("(node:1) DeprecationWarning: stale action runtime", 1, ["(?:^|[ >])DeprecationWarning:"]),
        (
            (
                "Job succeeded\n"
                '"forbidden_log_patterns": '
                '["(?:^|[ >])DeprecationWarning:", "(?:^|[ >])WARNING:"]'
            ),
            0,
            [],
        ),
    ],
)
def test_local_emulator_log_warning_policy(
    monkeypatch, tmp_path: Path, stdout: str, expected_code: int, warnings: list[str]
) -> None:
    ci = _load_ci_templates_module()
    entry = {
        "provider": "github",
        "projection": ".github/workflows/ci.yml",
        "template": ".config/ci/templates/hosted/github-actions.yml",
        "emulator_tool": "act",
        "emulator_event": "workflow_dispatch",
        "emulator_job": "quality",
        "emulator_image": (
            "ghcr.io/catthehacker/ubuntu@sha256:"
            "148374205122af210a8ca475111dd1a2934a10bbeea39b53850041517dccc570"
        ),
        "emulator_timeout_seconds": 1800,
        "forbidden_log_patterns": ["(?:^|[ >])DeprecationWarning:", "(?:^|[ >])WARNING:"],
    }
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    monkeypatch.setattr(ci.shutil, "which", {"act": "/usr/local/bin/act"}.get)
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(
        ci,
        "materialize_emulator_source",
        lambda **kwargs: {"source_dir": str(kwargs["state_dir"] / "source")},
    )
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda _command, **_: {"returncode": 0, "ok": True, "stdout": stdout, "stderr": ""},
    )
    output = tmp_path / "github-run.json"
    assert (
        ci.emulator_evidence(
            "github", mode="run", dry_run=False, allow_untracked=True, output=output
        )
        == expected_code
    )
    payload = json.loads(output.read_text())
    assert payload["verdict"] == ("pass" if expected_code == 0 else "block")
    assert payload["log_warnings"] == warnings


@pytest.mark.parametrize(("provider", "tool"), [("github", "act"), ("gitlab", "gitlab-ci-local")])
def test_container_emulator_uses_docker_context_when_no_endpoint_is_explicit(
    monkeypatch, tmp_path: Path, provider: str, tool: str
) -> None:
    ci, environment = _load_ci_templates_module(), {}
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(ci.shutil, "which", lambda _: "/usr/local/bin/tool")
    monkeypatch.setattr(ci, "_docker_context_endpoint", lambda: "unix:///context/docker.sock")
    monkeypatch.setattr(ci, "_tool_version", lambda _: f"{tool} 1.0")
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda _command, **kwargs: (
            environment.update(kwargs["env"])
            or {
                "returncode": 0,
                "ok": True,
                "stdout": "Job succeeded" if provider == "github" else "PASS selected job",
                "stderr": "",
            }
        ),
    )
    assert (
        ci.emulator_evidence(
            provider,
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=tmp_path / f"{provider}-run.json",
        )
        == 0
    )
    assert environment["DOCKER_HOST"] == "unix:///context/docker.sock"


def test_github_emulator_run_materializes_an_independent_git_source(
    monkeypatch, tmp_path: Path
) -> None:
    ci = _load_ci_templates_module()
    entry = {
        "provider": "github",
        "projection": ".github/workflows/ci.yml",
        "template": ".config/ci/templates/hosted/github-actions.yml",
        "emulator_tool": "act",
        "emulator_event": "workflow_dispatch",
        "emulator_job": "quality",
        "emulator_image": (
            "ghcr.io/catthehacker/ubuntu@sha256:"
            "148374205122af210a8ca475111dd1a2934a10bbeea39b53850041517dccc570"
        ),
        "emulator_timeout_seconds": 1800,
        "emulator_state_dir": "build/runtime/work/github-act",
    }
    summary = {
        "branch": "work/example",
        "head": "expected-head",
        "dirty": False,
        "status_short": "",
        "changed_scope": {
            "staged_paths": [],
            "unstaged_paths": [],
            "tracked_changed_paths": [],
            "untracked_count": 0,
            "untracked_preview": [],
            "untracked_preview_limit": 12,
        },
    }
    recorded = {}

    def materialize(**kw):
        source_dir = kw["state_dir"] / "source"
        source_dir.mkdir(parents=True)
        materialization = {
            "kind": "independent_git_checkout",
            "source_dir": str(source_dir),
            "source_head": "expected-head",
            "source_head_matches_expected": True,
            "git_directory_is_real": True,
            "uses_external_object_alternates": False,
            "tracked_diff_bytes": 0,
        }
        recorded["materialization"] = kw
        return materialization

    monkeypatch.setattr(ci, "ROOT", tmp_path)
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    monkeypatch.setattr(ci.shutil, "which", lambda _: "/usr/local/bin/act")
    monkeypatch.setattr(ci, "_docker_context_endpoint", lambda: "")
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(ci, "_git_summary", lambda: summary)
    monkeypatch.setattr(ci, "materialize_emulator_source", materialize, raising=False)
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda command, **kw: (
            recorded.update(command=command, run=kw)
            or {"returncode": 0, "ok": True, "stdout": "Job succeeded", "stderr": ""}
        ),
    )
    assert (
        ci.emulator_evidence(
            "github",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=tmp_path / "github-run.json",
        )
        == 0
    )
    state_dir = recorded["materialization"]["state_dir"]
    assert recorded["materialization"] == {
        "source_root": tmp_path,
        "state_dir": state_dir,
        "expected_head": "expected-head",
        "expected_branch": "work/example",
    }
    assert not state_dir.is_relative_to(tmp_path)
    assert recorded["run"]["cwd"] == state_dir / "source"
    assert not state_dir.exists()
    payload = json.loads((tmp_path / "github-run.json").read_text())
    assert payload["materialization"]["source_retained"] is False
