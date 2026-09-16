"""Installed command and SDK observations preserve explicit result boundaries."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.ci.delivery.acceptance import adopter as fixture
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import invocation
from tools.ci.delivery.acceptance import lane
from tools.ci.delivery.acceptance.receipt import REQUIRED_LIFECYCLE_STAGES

ROOT = Path(__file__).resolve().parents[4]


def test_adopter_is_clean_under_host_autocrlf(monkeypatch, tmp_path: Path) -> None:
    dirty = importlib.import_module("ethos.adapters.repo.dirty.change_provenance")
    global_config = tmp_path / "global.gitconfig"
    global_config.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

    def run(*command: str, cwd: Path | None = None) -> str:
        return subprocess.check_output(command, cwd=cwd, text=True).strip()

    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=run,
    )
    assert fixture.line_ending_conformance(adopter, run=run) == ["lf", "crlf"]

    readme = adopter / "README.md"
    readme.write_bytes(readme.read_bytes().replace(b"\n", b"\r\n"))
    run("git", "add", "README.md", cwd=adopter)

    assert b"\r\n" in readme.read_bytes()
    assert run("git", "status", "--porcelain", cwd=adopter) == ""
    assert dirty.dirty_provenance(adopter)["state"] == "clean"


@pytest.mark.parametrize("historical", [False, True])
def test_signature_acceptance_exercises_the_real_isolated_command_boundary(tmp_path, historical):
    def run(*command: str, cwd: Path | None = None) -> str:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=20,
        )
        return completed.stdout.strip()

    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=run,
    )
    fixture.prepare_acceptance_topology(adopter, run=run)
    observed = lane.prove_signature_repair(
        Path(sys.executable), adopter, environment={}, historical=historical
    )
    assert observed["state"] == "passed"
    assert observed["head"] != observed["previous_head"]
    assert observed["candidate_unchanged"] is True
    assert observed["remote_unchanged"] is True
    assert observed["reproof_executed"] is True
    assert observed["proof_subject"] == f"git:commit:{observed['head']}"
    assert observed["publication_readiness"] == "local_publish_ready"


def _blocked_command(command, gap, next_action):
    return {
        "schema_version": 2,
        "command": command,
        "verdict": "block",
        "state": "blocked",
        "summary": {},
        "diagnostics": [],
        "required_gaps": [gap],
        "next_action": next_action,
        "user_decision_required": False,
        "data": {},
        "continuation": "blocked",
        "missing_facts_or_evidence": [],
    }


def test_lane_lifecycle_failure_preserves_the_command_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = _blocked_command(
        "lane start", "candidate_worktree_missing", "ethos lane repair --root /repo --json"
    )
    monkeypatch.setattr(
        lane,
        "invoke",
        lambda *_args, **_kwargs: (
            1,
            result,
            json.dumps(result, sort_keys=True, separators=(",", ":")),
        ),
    )

    with pytest.raises(RuntimeError) as error:
        lane.prove_lifecycle(Path("/runtime/python"), tmp_path, environment={})

    assert str(error.value).startswith("package_lane_bootstrap_failed:")
    assert '"required_gaps":["candidate_worktree_missing"]' in str(error.value)
    assert '"next_action":"ethos lane repair --root /repo --json"' in str(error.value)


def test_package_cli_invocation_preserves_result_and_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    result = _blocked_command("status", "locked_environment_not_provisioned", "uv sync --frozen")
    monkeypatch.setattr(
        invocation,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=2,
            stdout=json.dumps(result),
            stderr="locked dependency unavailable",
        ),
    )

    returncode, observed, diagnostic = invocation.invoke(
        tmp_path,
        ("/runtime/ethos", "status", "--json"),
        environment={"PATH": "/native"},
    )

    assert returncode == 2
    assert observed == result
    assert '"required_gaps":["locked_environment_not_provisioned"]' in diagnostic
    assert diagnostic.endswith("stderr:locked dependency unavailable")


def test_lane_lifecycle_reuses_the_public_started_lane_for_recovery() -> None:
    prove_lifecycle = getattr(lane, "prove_lifecycle", None)

    assert callable(prove_lifecycle), "lane acceptance has no single public lifecycle owner"
    assert not hasattr(fixture, "seed_retirement_lease")


def test_package_lifecycle_requires_native_merge_acceptance() -> None:
    """Fixture-only GREEN cannot satisfy installed merge continuation acceptance."""
    assert "native_merge" in REQUIRED_LIFECYCLE_STAGES


def test_installed_sdk_check_observes_without_mutating_or_authoring_intent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke, adopter = tmp_path / "venv", tmp_path / "adopter"
    adopter.mkdir()
    executed: list[tuple[str, ...]] = []

    def run(*command: str, **_kwargs: object) -> str:
        executed.append(command)
        if command[-1] == "--version":
            return "ethos 0.2.0-alpha.3"
        if "Path(ethos.__file__)" in " ".join(command):
            return (smoke / "site-packages/ethos/__init__.py").as_posix()
        if "status" in command:
            return "{}"
        return ""

    monkeypatch.setattr(effect, "_run", run)
    monkeypatch.setattr(
        effect,
        "run_command",
        lambda *_args, **_kwargs: pytest.fail("SDK observation must not mutate lifecycle state"),
    )

    assert effect.observe_installed_package(smoke, adopter) == (
        (smoke / "site-packages/ethos/__init__.py").as_posix(),
        "ethos 0.2.0-alpha.3",
    )
    rendered = "\n".join(" ".join(command) for command in executed)
    assert "archive-change" not in rendered
    assert "rebuild-from" not in rendered
    assert "Commitment" not in rendered


def test_independent_cli_checks_do_not_replace_a_blocked_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []
    head = "a" * 40

    monkeypatch.setattr(
        effect,
        "_independent_host_environment",
        lambda: ({"PATH": "/native"}, "/native/git"),
    )

    def run_command(_root: Path, command: tuple[str, ...], **_kwargs: object):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout=f"{head}\n", stderr="")

    def invoke(_root: Path, command: tuple[str, ...], **_kwargs: object):
        commands.append(command)
        payload: dict[str, object] = {
            "schema_version": 2,
            "command": command[1],
            "verdict": "pass",
            "state": "ready",
            "required_gaps": [],
            "next_action": "",
            "data": {},
        }
        returncode = 0
        if command[1:3] == ("plan", "--changed"):
            payload.update(
                verdict="block",
                state="blocked",
                required_gaps=["change_generation_binding_invalid"],
                next_action="ethos lane repair --root /repo --json",
            )
            returncode = 1
        elif command[1:3] == ("publish", "--ref"):
            payload["data"] = {
                "transition_plan": {"effect": {"operation": "git.ref.compare-and-swap"}}
            }
        return returncode, payload, json.dumps(payload)

    monkeypatch.setattr(effect, "run_command", run_command)
    monkeypatch.setattr(effect.cli_invocation, "invoke", invoke)

    observation = effect.observe_independent_command_plane(tmp_path / "ethos", tmp_path)

    assert isinstance(observation["commands"], list)
    assert "plan --changed" in observation["commands"]
    assert sum(command[1:3] == ("plan", "--changed") for command in commands) == 1
    assert not any(command[1] == "plan" and "--changed" not in command for command in commands[1:])
