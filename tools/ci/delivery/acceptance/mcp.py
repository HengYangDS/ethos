"""Share real CLI, SDK and MCP conformance between source and installed acceptance."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from ethos.domain.adoption import adopt_repository
from ethos.domain.inspection import inspect_repository
from ethos.domain.land.operation import land_repository
from ethos.domain.plan import plan_repository
from ethos.domain.publication.operation import publish_repository


def _run(
    command: tuple[str, ...], root: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=root,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _git(root: Path, git: str, env: dict[str, str], *arguments: str) -> None:
    """Run fixture Git with one credential-free identity and isolated hook policy."""
    result = _run(
        (
            git,
            "-c",
            "user.name=ETHOS Conformance",
            "-c",
            "user.email=conformance@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=",
            *arguments,
        ),
        root,
        env,
    )
    assert result.returncode == 0, result.stderr


def _initialize(root: Path, git: str, env: dict[str, str]) -> None:
    root.mkdir()
    _git(root, git, env, "init", "--quiet", "--initial-branch=dev")
    _git(root, git, env, "commit", "--allow-empty", "--quiet", "-m", "initialize conformance")


async def _call(
    surface: str,
    client: Client,
    command: tuple[str, ...],
    root: Path,
    name: str,
    arguments: dict[str, Any],
    env: dict[str, str],
) -> dict[str, Any]:
    if surface == "mcp":
        result = await client.call_tool(name, arguments)
        assert not result.is_error
        assert result.structured_content is not None
        return result.structured_content
    if surface == "sdk":
        operation = {
            "status": inspect_repository,
            "plan": plan_repository,
            "adopt": adopt_repository,
            "land": land_repository,
            "publish": publish_repository,
        }[name]
        return operation(root, **arguments).to_dict()
    options: list[str] = []
    for key, value in arguments.items():
        if value is not False:
            options.append("--" + key.replace("_", "-"))
            if value is not True:
                options.append(str(value))
    completed = _run((*command, name, "--root", str(root), "--json", *options), root.parent, env)
    assert completed.returncode in {0, 1}, completed.stderr
    assert not completed.stderr, completed.stderr
    return json.loads(completed.stdout)


async def _adoption(
    surface: str,
    command: tuple[str, ...],
    root: Path,
    foreign: Path,
    env: dict[str, str],
    git: str,
) -> None:
    transport = StdioTransport(
        command[0],
        [*command[1:], "mcp", "--root", str(root)],
        cwd=str(root.parent),
        env=env,
        keep_alive=False,
    )
    async with Client(transport, timeout=30) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert set(tools) == {"status", "plan", "adopt", "land", "publish"}
        for tool in tools.values():
            assert tool.input_schema.get("additionalProperties") is False
            assert not {"root", "actor"} & tool.input_schema.get("properties", {}).keys()
            assert tool.output_schema["type"] == "object"
        for arguments in ({"root": str(foreign)}, {"actor": "foreign"}, {"apply": "true"}):
            rejected = await client.call_tool("adopt", arguments, raise_on_error=False)
            assert rejected.is_error
            assert not (root / ".ethos").exists()
            assert not (foreign / ".ethos").exists()
        preview = await _call("sdk", client, command, root, "adopt", {}, env)
        for caller in ("cli", "mcp"):
            assert await _call(caller, client, command, root, "adopt", {}, env) == preview
        exact = {
            "apply": True,
            "authorize": True,
            "expect_head": preview["data"]["mutation"]["current_head"],
            "expect_plan_digest": preview["data"]["plan_digest"],
        }
        for override in (
            {"authorize": False},
            {"expect_head": "0" * 40},
            {"expect_plan_digest": "0" * 64},
        ):
            denied = await _call("sdk", client, command, root, "adopt", exact | override, env)
            assert denied["verdict"] == "block"
            for caller in ("cli", "mcp"):
                assert (
                    await _call(caller, client, command, root, "adopt", exact | override, env)
                    == denied
                )
            assert not (root / ".ethos").exists()
        applied = await _call(surface, client, command, root, "adopt", exact, env)
        assert applied["verdict"] == "pass"
        assert applied["data"]["applied"] is True
        assert set(applied["data"]["planned_files"]) == {
            ".ethos/profile.toml",
            "openspec/config.yaml",
        }
        retained = {
            root / item["path"]: item["content_sha256"] for item in preview["data"]["write_plan"]
        }
        assert all(
            hashlib.sha256(path.read_bytes()).hexdigest() == value
            for path, value in retained.items()
        )
        before = {path: (path.stat().st_ino, path.stat().st_mtime_ns) for path in retained}
        for caller in ("sdk", "cli", "mcp"):
            stale = await _call(caller, client, command, root, "adopt", exact, env)
            assert stale["verdict"] == "block"
            assert not stale["data"]["applied"]
        assert before == {path: (path.stat().st_ino, path.stat().st_mtime_ns) for path in retained}
    async with Client(transport, timeout=30) as client:
        assert (await client.call_tool("status")).structured_content == inspect_repository(
            root
        ).to_dict()
        if surface == "mcp":
            _git(root, git, env, "add", "--", *(str(p.relative_to(root)) for p in retained))
            _git(root, git, env, "commit", "--quiet", "-m", "accept conformance adoption")
            await _observations(client, command, root, env)
        assert all(
            hashlib.sha256(path.read_bytes()).hexdigest() == value
            for path, value in retained.items()
        )


async def _observations(
    client: Client, command: tuple[str, ...], root: Path, env: dict[str, str]
) -> None:
    """Compare successful planning and live profile failure once across all transports."""
    planning = plan_repository(root, changed=True).to_dict()
    assert (planning["verdict"], planning["state"]) == ("pass", "no_changes"), planning
    for caller in ("cli", "mcp"):
        assert (
            await _call(caller, client, command, root, "plan", {"changed": True}, env) == planning
        )
    profile = root / ".ethos/profile.toml"
    original = profile.read_bytes()
    try:
        profile.write_text("not valid TOML [")
        before = profile.read_bytes(), profile.stat().st_ino, profile.stat().st_mtime_ns
        for name in ("status", "plan", "adopt", "land", "publish"):
            refused = await _call("sdk", client, command, root, name, {}, env)
            assert refused["verdict"] == "block"
            code = "adoption_conflict" if name == "adopt" else "repository_profile_invalid"
            assert refused["required_gaps"] == [f"{code}:.ethos/profile.toml"], refused
            for caller in ("cli", "mcp"):
                assert await _call(caller, client, command, root, name, {}, env) == refused
        assert (profile.read_bytes(), profile.stat().st_ino, profile.stat().st_mtime_ns) == before
    finally:
        profile.write_bytes(original)


async def _native_failure(
    command: tuple[str, ...], root: Path, git: str, env: dict[str, str]
) -> None:
    """Remove only a private Git locator after initialization; prove recovery on the same server."""
    with tempfile.TemporaryDirectory(prefix="native-git-", dir=root.parent) as directory:
        locator = Path(directory) / "git"
        locator.symlink_to(git)
        isolated = dict(env, PATH=directory)
        transport = StdioTransport(
            command[0],
            [*command[1:], "mcp", "--root", str(root)],
            cwd=str(root.parent),
            env=isolated,
            keep_alive=False,
        )
        async with Client(transport, timeout=30) as client:
            await client.list_tools()
            locator.unlink()
            previous = dict(os.environ)
            try:
                os.environ.clear()
                os.environ.update(isolated)
                for name in ("status", "plan", "adopt", "land", "publish"):
                    expected = await _call("sdk", client, command, root, name, {}, isolated)
                    assert expected["verdict"] == "block"
                    assert expected["required_gaps"] == ["git_executable_unavailable"]
                    assert expected["data"]["cwd"] == str(root)
                    for surface in ("cli", "mcp"):
                        assert (
                            await _call(surface, client, command, root, name, {}, isolated)
                            == expected
                        )
            finally:
                os.environ.clear()
                os.environ.update(previous)
                locator.symlink_to(git)
            assert (await client.call_tool("adopt")).structured_content == adopt_repository(
                root
            ).to_dict()


def verify(command: tuple[str, ...], workspace: Path) -> dict[str, object]:
    """Verify isolated real effects without modifying an existing adopter or product source."""
    git = shutil.which("git")
    assert git is not None, "Git is required for conformance setup"
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    before = dict(os.environ), Path.cwd()
    with tempfile.TemporaryDirectory(prefix="mcp-conformance-", dir=workspace) as directory:
        base = Path(directory)
        foreign = base / "foreign"
        _initialize(foreign, git, env)
        failed = _run(
            (*command, "mcp", "--root", str(foreign)),
            base,
            dict(env, PATH=str(base / "missing-native-tools")),
        )
        assert failed.returncode == 1
        assert not failed.stdout
        assert "install Git" in failed.stderr
        assert "Traceback" not in failed.stderr
        for surface in ("cli", "sdk", "mcp"):
            root = base / surface
            _initialize(root, git, env)
            asyncio.run(_adoption(surface, command, root, foreign, env, git))
        if os.name == "posix":
            asyncio.run(_native_failure(command, root, git, env))
        assert not (foreign / ".ethos").exists()
    assert (dict(os.environ), Path.cwd()) == before
    return {
        "state": "passed",
        "mutation_surfaces": ["cli", "sdk", "mcp"],
        "planning_no_changes": "passed",
        "profile_refusal": "passed",
        "native_git_loss": "passed" if os.name == "posix" else "not_qualified",
        "owned_work_removed": not Path(directory).exists(),
    }


if __name__ == "__main__":
    print(json.dumps(verify((sys.argv[1],), Path(sys.argv[2])), sort_keys=True))
