"""Installed command and SDK observations preserve explicit result boundaries."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.adapters.process import run_command
from ethos.result import EthosResult
from tools.ci.delivery.acceptance import adopter as fixture
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import invocation
from tools.ci.delivery.acceptance import lane

ROOT = Path(__file__).resolve().parents[4]


def _run(*command: str, cwd: Path | None = None) -> str:
    assert "--json" not in command, "Structured tools must use their semantic owner"
    return run_command(cwd or ROOT, command, timeout=20, check=True).stdout.strip()


def test_adopter_is_clean_under_host_autocrlf(monkeypatch, tmp_path: Path) -> None:
    dirty = importlib.import_module("ethos.adapters.repo.dirty.change_provenance")
    global_config = tmp_path / "global.gitconfig"
    global_config.write_text("[core]\n\tautocrlf = true\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=_run,
    )
    assert fixture.line_ending_conformance(adopter, run=_run) == ["lf", "crlf"]

    readme = adopter / "README.md"
    readme.write_bytes(readme.read_bytes().replace(b"\n", b"\r\n"))
    _run("git", "add", "README.md", cwd=adopter)

    assert b"\r\n" in readme.read_bytes()
    assert _run("git", "status", "--porcelain", cwd=adopter) == ""
    assert dirty.dirty_provenance(adopter)["state"] == "clean"


@pytest.mark.parametrize("historical", [False, True])
def test_signature_acceptance_exercises_the_real_isolated_command_boundary(tmp_path, historical):
    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=_run,
    )
    fixture.prepare_acceptance_topology(adopter, run=_run)
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
    return EthosResult(
        command=command,
        verdict="block",
        state="blocked",
        required_gaps=(gap,),
        next_action=next_action,
    ).to_dict()


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


@pytest.mark.parametrize("selection", ["", "adopter-change"])
def test_package_cli_invocation_preserves_result_and_isolates_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, selection: str
) -> None:
    """Actual child execution retains explicit context but not the parent repository."""
    monkeypatch.setenv("ETHOS_CHANGE", "foreign-change")
    monkeypatch.setenv("ETHOS_ACTOR", "foreign-actor")
    result = _blocked_command("status", "locked_environment_not_provisioned", "uv sync --frozen")
    code = (
        "import os,json,sys; p=json.loads(sys.argv[1]); "
        "p['data']={k:os.getenv(k,'') for k in ('ETHOS_CHANGE','ETHOS_ACTOR')}; "
        "print(json.dumps(p)); print('locked dependency unavailable',file=sys.stderr); sys.exit(2)"
    )
    returncode, observed, diagnostic = invocation.invoke(
        tmp_path,
        (sys.executable, "-I", "-c", code, json.dumps(result)),
        environment={"ETHOS_CHANGE": selection, "ETHOS_ACTOR": "adopter-actor"}
        if selection
        else {},
    )
    result["data"] = {
        "ETHOS_CHANGE": selection,
        "ETHOS_ACTOR": "adopter-actor" if selection else "",
    }
    assert returncode == 2
    assert observed == result
    assert '"required_gaps":["locked_environment_not_provisioned"]' in diagnostic
    assert diagnostic.endswith("stderr:locked dependency unavailable")


def test_installed_observation_runs_shared_isolated_conformance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    smoke, adopter = tmp_path / "venv", tmp_path / "adopter"
    adopter.mkdir()
    executed: list[tuple[str, ...]] = []

    def run(*command: str, **_kwargs: object) -> str:
        executed.append(command)
        if "--version" in command:
            return "ethos 0.2.0-alpha.3"
        if "Path(ethos.__file__)" in " ".join(command):
            return (smoke / "site-packages/ethos/__init__.py").as_posix()
        if "status" in command:
            return "{}"
        if len(command) > 3 and Path(command[3]).name == "mcp.py":
            return '{"state":"passed","native_git_loss":"not_qualified"}'
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
        {"state": "passed", "native_git_loss": "not_qualified"},
    )
    rendered = "\n".join(" ".join(command) for command in executed)
    assert "archive-change" not in rendered
    assert "rebuild-from" not in rendered
    assert "Commitment" not in rendered
    probe = executed[-1]
    assert Path(probe[0]).is_relative_to(smoke)
    assert Path(probe[0]).stem == "python"
    assert probe[1:3] == ("-B", "-I")
    assert probe[3] == str(Path(effect.__file__).with_name("mcp.py"))
    assert Path(probe[4]).is_relative_to(smoke)
    assert Path(probe[4]).stem == "ethos"
    assert probe[5] == str(effect.WORK)


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
        payload = EthosResult(command=command[1], verdict="pass", state="ready").to_dict()
        if command[1:3] == ("plan", "--changed"):
            payload = _blocked_command(
                command[1],
                "change_generation_binding_invalid",
                "ethos lane repair --root /repo --json",
            )
        elif command[1:3] == ("publish", "--ref"):
            payload["data"] = {
                "transition_plan": {"effect": {"operation": "git.ref.compare-and-swap"}}
            }
        return int(payload["verdict"] != "pass"), payload, json.dumps(payload)

    monkeypatch.setattr(effect, "run_command", run_command)
    monkeypatch.setattr(effect.cli_invocation, "invoke", invoke)

    observation = effect.observe_independent_command_plane(tmp_path / "ethos", tmp_path)

    assert isinstance(observation["commands"], list)
    assert "plan --changed" in observation["commands"]
    assert sum(command[1:3] == ("plan", "--changed") for command in commands) == 1
    assert not any(command[1] == "plan" and "--changed" not in command for command in commands[1:])
