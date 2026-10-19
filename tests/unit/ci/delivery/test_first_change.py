"""The installed first Change qualifies lane admission, Agent handoff and source format."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ethos.repository.release.resources import packaged_resource
from tests.support.installed_guidance import installed_guidance
from tools.ci.delivery.acceptance import first_change

_FORMAT_HEAD = "c" * 40


def _format_response(root: Path, request: tuple[str, ...], *, fail_apply: bool):
    """Simulate one native lane format report while preserving the actual consumer protocol."""
    paths = request[3 : request.index("--root")]
    candidates = {
        path: (root / path).read_bytes().replace(b"   ", b" ").replace(b"  \n", b"\n")
        for path in paths
    }
    changed = [path for path in paths if candidates[path] != (root / path).read_bytes()]
    if "--check" in request:
        state = "failed" if changed else "passed"
    elif "--apply" in request:
        assert "--authorize" in request
        assert request[request.index("--expect-head") + 1] == _FORMAT_HEAD
        state = "blocked" if fail_apply else "formatted"
        for path, content in {} if fail_apply else candidates.items():
            (root / path).write_bytes(content)
    else:
        state = "ready"
    refused = state in {"failed", "blocked"}
    report = {"verdict": "block" if refused else "pass", "state": state, "head": _FORMAT_HEAD}
    return int(refused), {**report, "data": {**report, "changed_paths": changed}}, ""


def _first_change_protocol(
    monkeypatch, lane_root: Path, status, executable: Path, command: Path, *, fail_format=False
):
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
        elif request[1:3] == ("lane", "format"):
            return _format_response(lane_root, request, fail_apply=fail_format)
        else:
            assert request[1:3] == ("lane", "prewrite")
        return 0, report, ""

    def run(_root: Path, request: tuple[str, ...], **kwargs):
        if request[1] == "add":
            paths = tuple(request[request.index("--") + 1 :])
            assert all(Path(path).name.startswith("format-draft.") for path in paths)
            assert all(path.startswith("docs/") for path in paths)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if request[1:] == ("rev-parse", "HEAD"):
            return SimpleNamespace(returncode=0, stdout=f"{_FORMAT_HEAD}\n", stderr="")
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
    guide, origin, status = installed_guidance(package)
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
        ) == {"first_change": "lane_admitted", "agent_handoff": "passed", "formatting": "passed"}
        assert [selected[:2] for selected in executed] == [tuple(map(str, command))] * 2


@pytest.mark.parametrize("projection", ["resources", "data", "outside", "digest", "format_failure"])
def test_first_change_uses_native_packaged_resource_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, projection: str
) -> None:
    """Exercise resource admission through the public installed first-Change journey."""
    package = tmp_path / "installed/ethos"
    _guide, _origin, status = installed_guidance(
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
    calls, effects = _first_change_protocol(
        monkeypatch,
        lane_root,
        status,
        executable,
        command,
        fail_format=projection == "format_failure",
    )
    if projection == "resources":
        assert first_change.prove_first_change(
            executable, tmp_path, environment={"PATH": ""}, origin=str(package / "__init__.py")
        ) == {
            "first_change": "lane_admitted",
            "agent_handoff": "passed",
            "formatting": "passed",
        }
        assert [request[2] for request in effects] == ["new", "validate"]
        assert sum(request[1:3] == ("lane", "prewrite") for request in calls) == 4
        formats = [request for request in calls if request[1:3] == ("lane", "format")]
        assert [request[request.index("--json") + 1 :] for request in formats] == [
            (),
            ("--check",),
            ("--apply", "--authorize", "--expect-head", _FORMAT_HEAD),
            ("--check",),
        ]
        assert (lane_root / "openspec/changes/first-change/specs/foundation/spec.md").is_file()
    else:
        with pytest.raises(
            RuntimeError,
            match=r"installed_(first_change_tool_unavailable|agent_guidance_invalid|source_format_unproven)",
        ):
            first_change.prove_first_change(
                executable, tmp_path, environment={"PATH": ""}, origin=str(package / "__init__.py")
            )
        assert [request[2] for request in effects] == {"format_failure": ["new", "validate"]}.get(
            projection, []
        )
