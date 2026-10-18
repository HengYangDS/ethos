"""Installed command and SDK observations preserve explicit result boundaries."""

from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)
from ethos.adapters.toolchain.mise import native_tool_cache
from ethos.repository.release.identity import build_identity
from ethos.repository.release.resources import GUIDANCE_RESOURCE
from ethos.repository.release.resources import packaged_resource
from ethos.result import EthosResult
from tools.ci.delivery.acceptance import adopter as fixture
from tools.ci.delivery.acceptance import brownfield as brownfield_fixture
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import first_change
from tools.ci.delivery.acceptance import invocation
from tools.ci.delivery.acceptance import lane

ROOT = Path(__file__).resolve().parents[4]


def _installed_guidance(
    package: Path, content: str = "Run ethos status.\n", *, directory: str = "resources"
):
    """Materialize one installed guidance fixture with its exact status identity."""
    guide = package / directory / GUIDANCE_RESOURCE
    guide.parent.mkdir(parents=True)
    guide.write_text(content, encoding="utf-8")
    origin = package / "__init__.py"
    origin.write_text("", encoding="utf-8")
    guidance = {
        "authority": "product_projection",
        "media_type": "text/markdown",
        "path": str(guide),
        "sha256": hashlib.sha256(guide.read_bytes()).hexdigest(),
    }
    return guide, origin, {"governance_context": {"agent_guidance": guidance}}


def _first_change_protocol(monkeypatch, lane_root: Path, status, executable: Path, command: Path):
    """Bind resource cases to the same complete lane, handoff and native effects."""
    lane_root.mkdir()
    branch = "work/first-change"
    calls: list[tuple[str, ...]] = []
    effects: list[tuple[str, ...]] = []

    def invoke(_root: Path, request: tuple[str, ...], *, environment):
        calls.append(request)
        report = {"verdict": "pass"}
        if request[1:3] == ("lane", "start"):
            report["data"] = {
                "path": str(lane_root),
                "branch": branch,
                "lease": {"generation": 1, "expires_at": "2099-01-01T00:00:00Z"},
            }
        elif request[1:3] == ("lane", "handoff"):
            report["state"] = "transferred" if "--apply" in request else "planned"
            report["data"] = {
                "lease": {
                    "generation": 2,
                    "holder_ref": request[request.index("--target-holder-ref") + 1],
                }
            }
        elif request[1] == "status":
            report.update(status)
            successor = environment["ETHOS_ACTOR"].endswith(":successor")
            report["required_gaps"] = [
                "openspec_requested_change_missing:first-change"
                if successor
                else f"lease_holder_mismatch:{branch}"
            ]
        else:
            assert request[1:3] == ("lane", "prewrite")
        return 0, report, ""

    def run(_root: Path, request: tuple[str, ...], **kwargs):
        effects.append(request)
        assert request[:2] == (str(executable), str(command))
        assert not kwargs["inherit_environment"]
        assert kwargs["env"]["ETHOS_ACTOR"].endswith(":successor")
        if request[2] == "new":
            metadata = lane_root / "openspec/changes/first-change/.openspec.yaml"
            metadata.parent.mkdir(parents=True)
            metadata.write_text("schema: spec-driven\n", encoding="utf-8")
        report = {"summary": {"totals": {"items": 1, "passed": 1, "failed": 0}}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(report), stderr="")

    monkeypatch.setattr(first_change, "invoke", invoke)
    monkeypatch.setattr(first_change, "run_command", run)
    return calls, effects


@pytest.mark.parametrize(
    ("phase", "gap"),
    [
        ("clean", ""),
        ("preview", "installed_brownfield_preview_invalid"),
        ("apply", "installed_brownfield_authored_content_changed"),
    ],
)
def test_brownfield_conformance_checks_authored_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, gap: str
) -> None:
    """Check the content guard; the installed wheel is exercised by install smoke."""
    planned = [".ethos/profile.toml", "openspec/config.yaml"]
    stages: list[str] = []

    def invoke(root: Path, command: tuple[str, ...], **_kwargs):
        stage = "apply" if "--apply" in command else "preview"
        stages.append(stage)
        if stage == "preview":
            if phase == "preview":
                (root / "README.md").write_text("rewritten\n", encoding="utf-8")
            return (
                0,
                {"verdict": "pass", "data": {"planned_files": planned, "plan_digest": "a" * 64}},
                "",
            )
        for relative in planned:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("installed binding\n", encoding="utf-8")
        if phase == "apply":
            (root / "README.md").write_text("rewritten\n", encoding="utf-8")
        return 0, {"verdict": "pass"}, ""

    monkeypatch.setattr(brownfield_fixture, "invoke", invoke)
    environment, _git = effect.independent_host_environment()
    arguments = (tmp_path / "ethos", tmp_path)
    if gap:
        with pytest.raises(RuntimeError, match=gap):
            brownfield_fixture.prove_brownfield(*arguments, environment=environment, run=_run)
    else:
        result = brownfield_fixture.prove_brownfield(*arguments, environment=environment, run=_run)
        assert result == {
            "state": "passed",
            "authored_content_preserved": True,
            "planned_files": planned,
        }
    assert stages == (["preview"] if phase == "preview" else ["preview", "apply"])


def _run(*command: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    assert "--json" not in command, "Structured tools must use their semantic owner"
    return run_command(
        cwd or ROOT, command, env=env, inherit_environment=env is None, timeout=20, check=True
    ).stdout.strip()


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
def test_signature_acceptance_binds_source_supply_across_isolated_commands(tmp_path, historical):
    """Source-bound CLI tests pass only the validated native supply to child commands."""
    adopter = tmp_path / "adopter"
    fixture.materialize_adopter(
        adopter,
        openspec_config=ROOT / "openspec/config.yaml",
        run=_run,
    )
    fixture.prepare_acceptance_topology(adopter, run=_run)
    supply = resolve_node_package_supply(ROOT)
    observed = lane.prove_signature_repair(
        Path(sys.executable),
        adopter,
        environment={
            "ETHOS_NODE_PACKAGE_SUPPLY": supply.as_posix(),
            "ETHOS_CI_TOOL_CACHE_DIR": native_tool_cache(ROOT).as_posix(),
        },
        historical=historical,
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
    package = smoke / "site-packages/ethos"
    _guide, _origin, status = _installed_guidance(package)
    executed: list[tuple[str, ...]] = []

    def run(*command: str, **_kwargs: object) -> str:
        executed.append(command)
        if "--version" in command:
            return "ethos 0.2.0-alpha.3"
        if "Path(ethos.__file__)" in " ".join(command):
            return (smoke / "site-packages/ethos/__init__.py").as_posix()
        if "status" in command:
            return json.dumps(status)
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


@pytest.mark.parametrize(
    ("selection", "gap"),
    [
        ("current", ""),
        ("foreign-guidance", "installed_agent_guidance_invalid"),
        ("escaped-script", "installed_first_change_tool_unavailable"),
        ("escaped-node", "installed_first_change_tool_unavailable"),
        ("ambient-openspec", "installed_first_change_tool_unavailable"),
    ],
)
def test_first_change_uses_the_installed_guidance_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selection: str, gap: str
) -> None:
    """The first Change consumes the current package resource, not a historical layout."""
    package = tmp_path / "site-packages/ethos"
    guide, origin, status = _installed_guidance(package)
    command = [
        package / "resources/node/bin/node",
        package / "resources/node_modules/@fission-ai/openspec/bin/openspec.js",
    ]
    for path in command:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("package-owned executable\n", encoding="utf-8")
    status["governance_context"]["official_openspec"] = {
        "base_command": [str(path) for path in command]
    }

    environment = {"PATH": ""}
    context = status["governance_context"]
    if selection == "foreign-guidance":
        foreign = tmp_path / "foreign/ethos/resources/skills/ethos-repository-work/SKILL.md"
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(guide.read_bytes())
        context["agent_guidance"]["path"] = str(foreign)
    elif selection in {"escaped-script", "escaped-node"}:
        outside = tmp_path / "external-command"
        outside.write_text("external executable\n", encoding="utf-8")
        selected = command[selection == "escaped-script"]
        selected.unlink()
        selected.symlink_to(outside)
    elif selection == "ambient-openspec":
        ambient = tmp_path / "bin/openspec"
        ambient.parent.mkdir()
        ambient.write_text("external executable\n", encoding="utf-8")
        ambient.chmod(0o755)
        environment["PATH"] = str(ambient.parent)
    _calls, executed = _first_change_protocol(monkeypatch, tmp_path / "lane", status, *command)
    if gap:
        with pytest.raises(RuntimeError, match=gap):
            first_change.prove_first_change(
                tmp_path / "ethos", tmp_path, environment=environment, origin=str(origin)
            )
        assert executed == []
    else:
        assert first_change.prove_first_change(
            tmp_path / "ethos", tmp_path, environment=environment, origin=str(origin)
        ) == {"first_change": "lane_admitted", "agent_handoff": "passed"}
        assert [selected[:2] for selected in executed] == [tuple(map(str, command))] * 2


def test_formation_first_change_binds_the_selected_runtime_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Formation selects immutable supply before the first Change consumes guidance."""
    bootstrap = tmp_path / "bootstrap/ethos"
    _guide, origin, _status = _installed_guidance(bootstrap)
    selected_origin = tmp_path / "immutable/site-packages/ethos/__init__.py"
    build = build_identity(product="0.2.0-alpha.3", source_commit="a" * 40, source_tree="b" * 40)
    observed: list[str] = []

    def invoke(_root: Path, command: tuple[str, ...], **_kwargs: object) -> tuple:
        target = Path(command[command.index("--root") + 1])
        if "--create" in command:
            if "--apply" in command:
                if target.exists():
                    return 1, {"required_gaps": ["formation_target_exists"]}, ""
                target.mkdir()
                data = {"applied": True}
            else:
                data = {
                    "plan_digest": "a" * 64,
                    "candidate_worktree_path": str(target) + "-candidate",
                }
        else:
            data = {"hook_runtime": {"current": True}}
        return 0, {"verdict": "pass", "data": data}, ""

    def first(_executable: Path, _target: Path, **kwargs: object) -> dict[str, str]:
        observed.append(str(kwargs["origin"]))
        return {"first_change": "lane_admitted", "agent_handoff": "passed"}

    monkeypatch.setattr(fixture, "invoke", invoke)
    monkeypatch.setattr(fixture, "verify_formed", lambda *_args: "a" * 40)
    monkeypatch.setattr(fixture, "_verify_candidate", lambda *_args: None)
    monkeypatch.setattr(fixture, "prove_first_change", first)
    monkeypatch.setattr(fixture, "require_manifest", lambda *_args, **_kwargs: tmp_path / "python")
    monkeypatch.setattr(
        fixture,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stdout=str(selected_origin), stderr=""
        ),
    )

    fixture.prove_formation(
        tmp_path / "ethos",
        tmp_path,
        origin=str(origin),
        build=build,
        wheel_sha256="f" * 64,
        environment={"PATH": ""},
        run=_run,
    )

    assert observed == [str(selected_origin)]


def test_installed_guidance_must_match_the_package_that_served_status(tmp_path: Path) -> None:
    """An installed CLI cannot point an Agent at source or altered guidance."""
    package = tmp_path / "venv/site-packages/ethos"
    guide, origin, status = _installed_guidance(
        package, "Run ethos status and follow next_action.\n"
    )
    guidance = status["governance_context"]["agent_guidance"]

    def payload(value: dict[str, str] | None) -> str:
        return json.dumps({"governance_context": {"agent_guidance": value}})

    invocation.require_installed_guidance(payload(guidance), origin.as_posix())
    for altered in (
        None,
        guidance | {"path": (tmp_path / "source/SKILL.md").as_posix()},
        guidance | {"sha256": "0" * 64},
        guidance | {"authority": "repository_policy"},
    ):
        with pytest.raises(RuntimeError, match="installed_agent_guidance_invalid"):
            invocation.require_installed_guidance(payload(altered), origin.as_posix())

    outside = tmp_path / "source/SKILL.md"
    outside.parent.mkdir()
    outside.write_bytes(guide.read_bytes())
    guide.unlink()
    try:
        guide.symlink_to(outside)
    except OSError:
        pytest.skip("native symlink creation unavailable")
    with pytest.raises(RuntimeError, match="installed_agent_guidance_invalid"):
        invocation.require_installed_guidance(payload(guidance), origin.as_posix())


def test_independent_cli_checks_do_not_replace_a_blocked_request(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commands: list[tuple[str, ...]] = []
    head = "a" * 40

    monkeypatch.setattr(
        effect,
        "independent_host_environment",
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


@pytest.mark.parametrize("projection", ["resources", "data", "outside", "digest"])
def test_first_change_uses_native_packaged_resource_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, projection: str
) -> None:
    """Exercise resource admission through the public installed first-Change journey."""
    package = tmp_path / "installed/ethos"
    _guide, _origin, status = _installed_guidance(
        package, directory="data" if projection == "data" else "resources"
    )
    executable = packaged_resource("node/bin/node", package=package)
    command = (
        tmp_path / "foreign/cli.js"
        if projection == "outside"
        else packaged_resource("node_modules/openspec/cli.js", package=package)
    )
    for path in (executable, command):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    status["governance_context"]["official_openspec"] = {
        "base_command": [str(executable), str(command)]
    }
    if projection == "digest":
        status["governance_context"]["agent_guidance"]["sha256"] = "invalid"
    lane_root = tmp_path / "work"
    calls, effects = _first_change_protocol(monkeypatch, lane_root, status, executable, command)
    if projection == "resources":
        assert first_change.prove_first_change(
            executable, tmp_path, environment={"PATH": ""}, origin=str(package / "__init__.py")
        ) == {
            "first_change": "lane_admitted",
            "agent_handoff": "passed",
        }
        assert [request[2] for request in effects] == ["new", "validate"]
        assert sum(request[1:3] == ("lane", "prewrite") for request in calls) == 3
        assert (lane_root / "openspec/changes/first-change/specs/foundation/spec.md").is_file()
    else:
        with pytest.raises(
            RuntimeError, match=r"installed_(first_change_tool_unavailable|agent_guidance_invalid)"
        ):
            first_change.prove_first_change(
                executable, tmp_path, environment={"PATH": ""}, origin=str(package / "__init__.py")
            )
        assert effects == []
