"""Runtime contracts for local hosted-provider emulation."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_CONFIG = ROOT / ".config/checks/ci/templates.toml"
GITHUB_IMAGE = (
    "ghcr.io/catthehacker/ubuntu@sha256:"
    "148374205122af210a8ca475111dd1a2934a10bbeea39b53850041517dccc570"
)
GITHUB_EMULATOR = {
    "provider": "github",
    "projection": ".github/workflows/ci.yml",
    "template": ".config/ci/templates/hosted/github-actions.yml",
    "emulator_tool": "act",
    "emulator_event": "workflow_dispatch",
    "emulator_job": "quality",
    "emulator_image": GITHUB_IMAGE,
    "emulator_timeout_seconds": 1,
}


def _providers() -> dict[str, dict[str, object]]:
    entries = tomllib.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))["projection"]
    assert isinstance(entries, list)
    return {str(entry["provider"]): entry for entry in entries}


def _ci():
    spec = importlib.util.spec_from_file_location(
        "ethos_test_ci_templates_runtime", ROOT / "tools/ci/ci_templates.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary() -> dict[str, object]:
    return {
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


def _materialize(**kwargs: Any) -> dict[str, str]:
    source = kwargs["state_dir"] / "source"
    source.mkdir(parents=True)
    return {"source_dir": str(source)}


def _payload(ci: Any, tmp_path: Path, provider: str = "github") -> tuple[int, dict[str, Any]]:
    output = tmp_path / f"{provider}-run.json"
    code = ci.emulator_evidence(
        provider, mode="run", dry_run=False, allow_untracked=True, output=output
    )
    return code, json.loads(output.read_text(encoding="utf-8"))


def _stub_runtime(monkeypatch: pytest.MonkeyPatch, ci: Any, run, *, tool="act") -> None:
    monkeypatch.setattr(ci.shutil, "which", lambda _: f"/usr/local/bin/{tool}")
    monkeypatch.setattr(ci, "_tool_version", lambda selected: f"{selected} 1.0")
    monkeypatch.setattr(ci, "materialize_emulator_source", _materialize)
    monkeypatch.setattr(ci, "_run_command", run)


def test_local_emulator_run_persists_a_bounded_log_and_timeout_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ci = _ci()

    def time_out(*_args: object, **kwargs: Any) -> dict[str, object]:
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
    monkeypatch.setattr(ci, "_provider_entry", lambda _: GITHUB_EMULATOR)
    monkeypatch.setattr(ci, "_git_summary", _summary)
    _stub_runtime(monkeypatch, ci, time_out)

    code, payload = _payload(ci, tmp_path)

    log_path = Path(payload["log_path"])
    assert (code, payload["verdict"], payload["timed_out"], payload["timeout_seconds"]) == (
        124,
        "block",
        True,
        1,
    )
    assert log_path.read_text(encoding="utf-8") == "partial emulator output\n"


def test_emulator_materialization_preserves_branch_identity(tmp_path: Path) -> None:
    ci, source = _ci(), tmp_path / "source"
    source.mkdir()
    for command in (
        ("init", "--quiet", str(source)),
        ("-C", str(source), "checkout", "--quiet", "-b", "work/example"),
    ):
        subprocess.run(["git", *command], check=True)
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", source, "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", source, "commit", "--quiet", "-m", "test"], check=True)
    head = subprocess.run(
        ["git", "-C", source, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()

    result = ci.materialize_emulator_source(
        source_root=source,
        state_dir=tmp_path / "state",
        expected_head=head,
        expected_branch="work/example",
    )
    checkout = Path(result["source_dir"])
    branch = subprocess.run(
        ["git", "-C", checkout, "symbolic-ref", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert (result["source_branch"], result["source_branch_matches_expected"], branch) == (
        "work/example",
        True,
        "work/example",
    )


@pytest.mark.parametrize(
    ("mode", "expected", "verdict"), [("doctor", 0, "pass"), ("run", 127, "block")]
)
def test_local_emulator_missing_optional_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str, expected: int, verdict: str
) -> None:
    ci = _ci()
    monkeypatch.setattr(ci.shutil, "which", lambda _: None)
    output = None if mode == "doctor" else tmp_path / "gitlab-run.json"

    assert (
        ci.emulator_evidence(
            "gitlab", mode=mode, dry_run=False, allow_untracked=mode == "run", output=output
        )
        == expected
    )
    receipt = ROOT / "build/evidence/local-ci/gitlab/doctor.json" if output is None else output
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert (payload["tool_available"], payload["returncode"], payload["stderr"]) == (
        False,
        127,
        "tool not found",
    )
    assert payload["verdict"] == verdict
    if mode == "doctor":
        assert payload["hosted_gitlab_status_claimed"] is False
    else:
        assert payload["materialization"]["untracked_policy"] == "refuse_before_emulator_run"


def test_local_emulator_executes_each_selected_provider_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ci, commands, roots, states = _ci(), [], [], []

    def materialize(**kwargs: Any) -> dict[str, str]:
        state = kwargs["state_dir"]
        states.append(state)
        (state / "source").mkdir(parents=True)
        return {"source_dir": str(state / "source")}

    def run(command: list[str], **kwargs: Any) -> dict[str, object]:
        commands.append(command)
        roots.append(kwargs["cwd"])
        if command[0] == "gitlab-ci-local":
            assert (kwargs["cwd"] / command[command.index("--state-dir") + 1]).is_dir()
        return {
            "returncode": 0,
            "ok": True,
            "stdout": "Job succeeded" if command[0] == "act" else "PASS ethos:carrier-quality",
            "stderr": "",
        }

    providers = _providers()
    providers["github"] |= {"emulator_image": GITHUB_IMAGE}
    monkeypatch.setattr(ci, "_provider_entry", providers.__getitem__)
    _stub_runtime(monkeypatch, ci, run)
    monkeypatch.setattr(ci, "materialize_emulator_source", materialize)

    for provider, job in (("github", "quality"), ("gitlab", "ethos:carrier-quality")):
        code, payload = _payload(ci, tmp_path, provider)
        assert (code, payload["execution"]["selected_job"], payload["execution"]["executed"]) == (
            0,
            job,
            True,
        )
        assert payload["execution_environment"]["image_digest_status"] == "declaration_bound"
    assert commands[0][:7] == [
        "act",
        "workflow_dispatch",
        "-W",
        ".github/workflows/ci.yml",
        "-j",
        "quality",
        "--bind",
    ]
    assert commands[1][-1] == "ethos:carrier-quality"
    assert roots == [state / "source" for state in states]
    assert all(not state.is_relative_to(ROOT) and not state.exists() for state in states)


@pytest.mark.parametrize("stdout", ["Skipping unsupported platform", ""])
def test_github_zero_exit_without_steps_is_not_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout: str
) -> None:
    ci = _ci()
    _stub_runtime(
        monkeypatch,
        ci,
        lambda *_args, **_kwargs: {
            "returncode": 0,
            "ok": True,
            "stdout": stdout,
            "stderr": "",
        },
    )
    code, payload = _payload(ci, tmp_path)
    assert (code, payload["verdict"], payload["execution"]["executed"]) == (1, "block", False)


@pytest.mark.parametrize(
    ("stdout", "expected", "warnings"),
    [
        ("(node:1) DeprecationWarning: stale", 1, ["(?:^|[ >])DeprecationWarning:"]),
        (
            'Job succeeded\n"forbidden_log_patterns": ["(?:^|[ >])DeprecationWarning:"]',
            0,
            [],
        ),
    ],
)
def test_local_emulator_log_warning_policy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stdout: str,
    expected: int,
    warnings: list[str],
) -> None:
    ci = _ci()
    entry = GITHUB_EMULATOR | {
        "emulator_timeout_seconds": 1800,
        "forbidden_log_patterns": ["(?:^|[ >])DeprecationWarning:", "(?:^|[ >])WARNING:"],
    }
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    _stub_runtime(
        monkeypatch,
        ci,
        lambda *_args, **_kwargs: {
            "returncode": 0,
            "ok": True,
            "stdout": stdout,
            "stderr": "",
        },
    )
    code, payload = _payload(ci, tmp_path)
    assert (code, payload["log_warnings"]) == (expected, warnings)


@pytest.mark.parametrize(
    ("provider", "tool"), [("github", "act"), ("gitlab", "gitlab-ci-local")]
)
def test_container_emulator_uses_docker_context_when_no_endpoint_is_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, provider: str, tool: str
) -> None:
    ci, environment = _ci(), {}
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(ci, "_docker_context_endpoint", lambda: "unix:///context/docker.sock")

    def run(*_args: object, **kwargs: Any) -> dict[str, object]:
        environment.update(kwargs["env"])
        return {
            "returncode": 0,
            "ok": True,
            "stdout": "Job succeeded" if provider == "github" else "PASS selected job",
            "stderr": "",
        }

    _stub_runtime(monkeypatch, ci, run, tool=tool)
    assert _payload(ci, tmp_path, provider)[0] == 0
    assert environment["DOCKER_HOST"] == "unix:///context/docker.sock"


def test_github_run_materializes_an_independent_git_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ci, recorded = _ci(), {}
    entry = GITHUB_EMULATOR | {"emulator_timeout_seconds": 1800}

    def materialize(**kwargs: Any) -> dict[str, object]:
        source = kwargs["state_dir"] / "source"
        source.mkdir(parents=True)
        recorded["materialization"] = kwargs
        return {
            "kind": "independent_git_checkout",
            "source_dir": str(source),
            "source_head": "expected-head",
            "source_head_matches_expected": True,
            "git_directory_is_real": True,
            "uses_external_object_alternates": False,
            "tracked_diff_bytes": 0,
        }

    monkeypatch.setattr(ci, "ROOT", tmp_path)
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    monkeypatch.setattr(ci, "_git_summary", _summary)
    _stub_runtime(
        monkeypatch,
        ci,
        lambda command, **kwargs: (
            recorded.update(command=command, run=kwargs)
            or {"returncode": 0, "ok": True, "stdout": "Job succeeded", "stderr": ""}
        ),
    )
    monkeypatch.setattr(ci, "materialize_emulator_source", materialize)
    code, payload = _payload(ci, tmp_path)
    state = recorded["materialization"]["state_dir"]
    assert code == 0
    assert recorded["materialization"] == {
        "source_root": tmp_path,
        "state_dir": state,
        "expected_head": "expected-head",
        "expected_branch": "work/example",
    }
    assert not state.is_relative_to(tmp_path)
    assert recorded["run"]["cwd"] == state / "source"
    assert not state.exists()
    assert payload["materialization"]["source_retained"] is False
