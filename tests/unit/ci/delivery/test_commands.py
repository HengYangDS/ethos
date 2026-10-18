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
from ethos.repository.release.resources import GUIDANCE_RESOURCE
from ethos.repository.release.resources import packaged_resource
from ethos.result import EthosResult
from tools.ci.delivery.acceptance import adopter as fixture
from tools.ci.delivery.acceptance import brownfield as brownfield_fixture
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import first_change
from tools.ci.delivery.acceptance import invocation
from tools.ci.delivery.acceptance import lane
from tools.ci.delivery.acceptance.adopter import verify_formed

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("missing", ["", "git", "ssh-keygen"])
def test_independent_host_requires_its_signed_fixture_tools(monkeypatch, missing):
    """Supply both native prerequisites without inheriting unrelated host tooling."""
    which = effect.shutil.which
    monkeypatch.setattr(
        effect.shutil,
        "which",
        lambda name, **kwargs: None if name == missing else which(name, **kwargs),
    )
    if missing:
        with pytest.raises(RuntimeError, match=f"required executable is unavailable: {missing}"):
            effect.independent_host_environment()
    else:
        environment, _git = effect.independent_host_environment()
        assert all(which(name, path=environment["PATH"]) for name in ("git", "ssh-keygen"))


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


def test_installed_formation_observation_binds_the_effect_head(tmp_path: Path) -> None:
    """A formation plan is not the result; the applied effect owns the commit OID."""
    target = tmp_path / "formed"
    target.mkdir()
    entry = target / "AGENTS.md"
    entry.write_text("Run ethos status --root . --json\n", encoding="utf-8")
    guide = tmp_path / "SKILL.md"
    guide.write_text("Use the installed product.\n", encoding="utf-8")
    digest = hashlib.sha256(guide.read_bytes()).hexdigest()
    head = "a" * 40
    plan: dict[str, object] = {
        "write_plan": [
            {"path": "AGENTS.md", "content_sha256": hashlib.sha256(entry.read_bytes()).hexdigest()}
        ]
    }
    status: dict[str, object] = {
        "verdict": "pass",
        "data": {
            "head": head,
            "dirty": False,
            "hook_runtime": {"current": True},
            "candidate": {"worktree_exists": True},
        },
        "governance_context": {"agent_guidance": {"sha256": digest, "path": str(guide)}},
    }

    assert verify_formed(target, plan, {"effect": {"head": head}}, (0, status, ""), digest) == head
    with pytest.raises(RuntimeError, match="installed_formation_status_invalid"):
        verify_formed(target, plan, {"head": head}, (0, status, ""), digest)


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
    guide = package / "resources/skills/ethos-repository-work/SKILL.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("Run ethos status.\n", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    executed: list[tuple[str, ...]] = []
    environments: list[object] = []
    environment, _git = effect.independent_host_environment()
    environment["XDG_DATA_HOME"] = str(tmp_path / "host-data")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "ambient-data"))

    def run(*command: str, **_kwargs: object) -> str:
        executed.append(command)
        environments.append(_kwargs.get("env"))
        if "--version" in command:
            return "ethos 0.2.0-alpha.3"
        if "Path(ethos.__file__)" in " ".join(command):
            return (smoke / "site-packages/ethos/__init__.py").as_posix()
        if "status" in command:
            return json.dumps(
                {
                    "governance_context": {
                        "agent_guidance": {
                            "authority": "product_projection",
                            "media_type": "text/markdown",
                            "path": str(guide),
                            "sha256": hashlib.sha256(guide.read_bytes()).hexdigest(),
                        }
                    }
                }
            )
        if len(command) > 3 and Path(command[3]).name == "mcp.py":
            return '{"state":"passed","native_git_loss":"not_qualified"}'
        return ""

    monkeypatch.setattr(effect, "_run", run)
    monkeypatch.setattr(
        effect,
        "run_command",
        lambda *_args, **_kwargs: pytest.fail("SDK observation must not mutate lifecycle state"),
    )

    assert effect.observe_installed_package(smoke, adopter, environment=environment) == (
        (smoke / "site-packages/ethos/__init__.py").as_posix(),
        "ethos 0.2.0-alpha.3",
        {"state": "passed", "native_git_loss": "not_qualified"},
    )
    assert environments
    assert all(value == environment for value in environments)
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


def test_installed_guidance_must_match_the_package_that_served_status(tmp_path: Path) -> None:
    """An installed CLI cannot point an Agent at source or altered guidance."""
    package = tmp_path / "venv/site-packages/ethos"
    guide = package / "resources/skills/ethos-repository-work/SKILL.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("Run ethos status and follow next_action.\n", encoding="utf-8")
    origin = package / "__init__.py"
    origin.write_text("", encoding="utf-8")
    guidance = {
        "authority": "product_projection",
        "media_type": "text/markdown",
        "path": str(guide),
        "sha256": hashlib.sha256(guide.read_bytes()).hexdigest(),
    }

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

    environment, _git = effect.independent_host_environment()

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

    observation = effect.observe_independent_command_plane(
        tmp_path / "ethos", tmp_path, environment=environment
    )

    assert isinstance(observation["commands"], list)
    assert "plan --changed" in observation["commands"]
    assert sum(command[1:3] == ("plan", "--changed") for command in commands) == 1
    assert not any(command[1] == "plan" and "--changed" not in command for command in commands[1:])


def _format_response(root: Path, request: tuple[str, ...], *, fail_apply: bool):
    """Simulate one native command result while preserving the actual consumer protocol."""
    paths = [part for part in request[2 : request.index("--root")] if not part.startswith("--")]
    candidates = {
        path: (root / path).read_bytes().replace(b"   ", b" ").replace(b"  \n", b"\n")
        for path in paths
    }
    changed = [path for path in paths if candidates[path] != (root / path).read_bytes()]
    applying = "--apply" in request
    if applying and not fail_apply:
        for path, content in candidates.items():
            (root / path).write_bytes(content)
    refusal = bool(changed) and "--check" in request
    state = "format_required" if refusal else "formatted" if applying else "planned"
    return (
        int(refusal),
        {
            "verdict": "block" if refusal else "pass",
            "data": {
                "state": state if changed else "conforming",
                "applied": applying and not fail_apply,
                "changed_paths": changed,
                "selected_paths": paths,
            },
        },
        "",
    )


def _first_change_effect(lane, executable, command, effects, request, **kwargs):
    """Execute the synthetic official artifact boundary or its independent native Git staging."""
    if request[1] == "add":
        paths = tuple(request[request.index("--") + 1 :])
        assert all(" [draft]" in path for path in paths)
        assert all(path.startswith("docs/") for path in paths)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    effects.append(request)
    assert request[:2] == (str(executable), str(command))
    assert not kwargs["inherit_environment"]
    assert kwargs["env"]["ETHOS_ACTOR"].endswith(":successor")
    if request[2] == "new":
        metadata = lane / "openspec/changes/first-change/.openspec.yaml"
        metadata.parent.mkdir(parents=True)
        metadata.write_text("schema: spec-driven\n", encoding="utf-8")
    report = {"summary": {"totals": {"items": 1, "passed": 1, "failed": 0}}}
    return SimpleNamespace(returncode=0, stdout=json.dumps(report), stderr="")


@pytest.mark.parametrize("projection", ["resources", "data", "outside", "digest", "format_failure"])
def test_first_change_uses_native_packaged_resource_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, projection: str
) -> None:
    """Exercise resource admission through the public installed first-Change journey."""
    package = tmp_path / "installed/ethos"
    guide = (
        package / "data" / GUIDANCE_RESOURCE
        if projection == "data"
        else packaged_resource(GUIDANCE_RESOURCE, package=package)
    )
    executable = tmp_path / "node"
    command = (
        tmp_path / "foreign/cli.js"
        if projection == "outside"
        else packaged_resource("node_modules/openspec/cli.js", package=package)
    )
    for path, content in {
        package / "__init__.py": "",
        guide: "Run ethos status.\n",
        executable: "",
        command: "",
    }.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    status: dict[str, object] = {
        "governance_context": {
            "official_openspec": {"base_command": [str(executable), str(command)]},
            "agent_guidance": {
                "path": str(guide),
                "authority": "product_projection",
                "media_type": "text/markdown",
                "sha256": "invalid"
                if projection == "digest"
                else hashlib.sha256(guide.read_bytes()).hexdigest(),
            },
        }
    }
    lane_root = tmp_path / "work"
    lane_root.mkdir()
    branch = "work/first-change"
    calls: list[tuple[str, ...]] = []
    effects: list[tuple[str, ...]] = []

    def invoke(_root: Path, request: tuple[str, ...], *, environment):
        calls.append(request)
        if request[1:3] == ("lane", "start"):
            return (
                0,
                {
                    "verdict": "pass",
                    "data": {
                        "path": str(lane_root),
                        "branch": branch,
                        "lease": {"generation": 1, "expires_at": "2099-01-01T00:00:00Z"},
                    },
                },
                "",
            )
        if request[1:3] == ("lane", "handoff"):
            applied = "--apply" in request
            return (
                0,
                {
                    "verdict": "pass",
                    "state": "transferred" if applied else "planned",
                    "data": {
                        "lease": {
                            "generation": 2,
                            "holder_ref": request[request.index("--target-holder-ref") + 1],
                        }
                    },
                },
                "",
            )
        if request[1] == "status":
            successor = environment["ETHOS_ACTOR"].endswith(":successor")
            return (
                0,
                {
                    **status,
                    "required_gaps": [
                        "openspec_requested_change_missing:first-change"
                        if successor
                        else f"lease_holder_mismatch:{branch}"
                    ],
                },
                "",
            )
        if request[1] == "format":
            return _format_response(lane_root, request, fail_apply=projection == "format_failure")
        assert request[1:3] == ("lane", "prewrite")
        return 0, {"verdict": "pass"}, ""

    def run(_root: Path, request: tuple[str, ...], **kwargs):
        return _first_change_effect(lane_root, executable, command, effects, request, **kwargs)

    monkeypatch.setattr(first_change, "invoke", invoke)
    monkeypatch.setattr(first_change, "run_command", run)
    if projection == "resources":
        assert first_change.prove_first_change(executable, tmp_path, environment={"PATH": ""}) == {
            "first_change": "lane_admitted",
            "agent_handoff": "passed",
            "formatting": "passed",
        }
        assert [request[2] for request in effects] == ["new", "validate"]
        assert sum(request[1:3] == ("lane", "prewrite") for request in calls) == 4
        assert (lane_root / "openspec/changes/first-change/specs/foundation/spec.md").is_file()
    else:
        with pytest.raises(
            RuntimeError,
            match=r"installed_(first_change_tool_unavailable|agent_guidance_invalid|source_format_unproven)",
        ):
            first_change.prove_first_change(executable, tmp_path, environment={"PATH": ""})
        assert [request[2] for request in effects] == {"format_failure": ["new", "validate"]}.get(
            projection, []
        )
