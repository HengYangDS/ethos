"""Quality sessions enforce native selection and execution boundaries."""

from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from unittest.mock import Mock

import pytest
import tomli_w

import ethos.repository.policy.schema as schema_owner
from ethos.adapters.process import run_command
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.ci import config_quality
from tools.ci import dependency_hygiene
from tools.ci import sessions

ROOT = Path(__file__).resolve().parents[2]


def test_noxfile_is_only_a_projection_of_repository_sessions() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    assert "sessions.PUBLIC_SESSIONS" in source
    assert "system/gates.toml" not in source
    assert "timeout" not in source
    assert not (ROOT / "tools/ci/registry.py").exists()
    assert not (ROOT / "tools/ci/runner.py").exists()


def test_machine_declared_nox_gates_are_implemented_by_sessions() -> None:
    public = set(sessions.PUBLIC_SESSIONS)
    assert len(public) == len(sessions.PUBLIC_SESSIONS)
    gates = tomllib.loads((ROOT / "system/gates.toml").read_text())["gates"]
    assert {
        command[-1]
        for item in gates
        if "nox" in (command := item.get("command", [])) and "-s" in command
    } <= public
    assert all(callable(getattr(sessions, name)) for name in public)


def test_project_runtime_is_the_only_executable_resolution_owner() -> None:
    consumers = (
        "tools/ci/sessions.py",
        "tools/ci/dependency_hygiene.py",
        "tools/ci/delivery/acceptance/effect.py",
        "tools/ci/delivery/pipeline.py",
    )
    for relative in consumers:
        assert "tools.ci.toolchain.environment" in (ROOT / relative).read_text(encoding="utf-8")


def test_pytest_git_environment_is_hermetic() -> None:
    count = int(os.environ["GIT_CONFIG_COUNT"])
    entries = tuple(
        (os.environ[f"GIT_CONFIG_KEY_{index}"], os.environ[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    )

    assert ("core.fsmonitor", "false") in entries
    assert len([key for key, _value in entries if key == "init.templateDir"]) == 1
    assert not {"user.name", "user.email"} & {key for key, _value in entries}
    assert all(value for _key, value in entries)
    assert os.environ["GIT_AUTHOR_NAME"] == "ETHOS Test"
    assert os.environ["GIT_AUTHOR_EMAIL"] == "test@example.invalid"
    assert os.environ["GIT_COMMITTER_NAME"] == "ETHOS Test"
    assert os.environ["GIT_COMMITTER_EMAIL"] == "test@example.invalid"
    assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    assert os.environ["GIT_TERMINAL_PROMPT"] == "0"


@pytest.mark.parametrize(("name", "filename"), [("lint", "alive.py"), ("shell_lint", "alive.sh")])
def test_quality_inventory_excludes_deleted_worktree_paths(tmp_path, monkeypatch, name, filename):
    """Both native inventory transports retain live paths and omit deleted ones."""
    (tmp_path / filename).write_text("# fixture\n", encoding="utf-8")
    inventory = f"{filename}\0deleted{Path(filename).suffix}\0"
    session = Mock()
    session.run.side_effect = lambda *args, **_kw: inventory if args[0] == "git" else ""
    monkeypatch.setattr(sessions, "ROOT", tmp_path)
    monkeypatch.setattr(sessions, "RUFF_CACHE", tmp_path / ".ruff-cache")
    monkeypatch.setattr(sessions.subprocess, "check_output", lambda *_a, **_kw: inventory.encode())
    getattr(sessions, name)(session)
    checked = [call.args for call in session.run.call_args_list if call.args[0] != "git"]
    assert checked
    if name == "shell_lint":
        assert [Path(args[0]).name for args in checked] == ["shellcheck", "shfmt"]
        assert "-d" in checked[1]
        assert "-w" not in checked[1]
    assert all(filename in args for args in checked)
    assert all(f"deleted{Path(filename).suffix}" not in args for args in checked)


def test_schema_gate_reuses_repository_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    validate = Mock(return_value={"verdict": "pass", "schema_count": 1, "required_gaps": []})
    monkeypatch.setattr(schema_owner, "schema_validation_report", validate)
    session = Mock()
    sessions.schemas(session)
    validate.assert_called_once_with(sessions.ROOT)
    session.log.assert_called_once()
    session.run.assert_not_called()
    session.error.assert_not_called()


def test_prose_executor_consumes_only_declared_policy_paths() -> None:
    calls = []
    sessions.prose(type("Session", (), {"run": lambda _, *args: calls.append(args)})())
    expected = [sessions.RUNTIME.script("codespell"), "--toml"]
    expected += [str(ROOT / ".config/checks/prose/codespell.toml"), "--count"]
    expected += ["--quiet-level=2", "README.md", "CONTRIBUTING.md", "AGENTS.md"]
    assert calls[0] == (*expected, "docs", "rules", "openspec/specs")


@pytest.mark.parametrize(
    ("arguments", "succeeds"),
    [(("--list",), True), (("-s", "lint"), True), (("-s", "markdown_lint"), False)],
)
def test_nox_requires_only_selected_node_supply(tmp_path, arguments, succeeds) -> None:
    """Native listing and Python lint stay usable without unrelated Node supply."""
    result = run_command(
        ROOT,
        (sys.executable, "-B", "-m", "nox", *arguments),
        env={"ETHOS_NODE_PACKAGE_SUPPLY": str(tmp_path / "missing")},
        timeout=60,
    )
    assert (result.returncode == 0) is succeeds, result.stdout + result.stderr
    assert ("node_package_supply_unavailable" in result.stderr) is not succeeds


def test_session_discovery_does_not_load_unselected_capabilities() -> None:
    """Inspect actual fresh-process imports rather than cached test-worker modules."""
    result = run_command(
        ROOT,
        (
            sys.executable,
            "-B",
            "-c",
            "import sys;from tools.ci import sessions;print(*sys.modules, sep=chr(10))",
        ),
        timeout=20,
        check=True,
    )
    assert "tools.ci.sessions" in result.stdout.splitlines()
    assert not {
        "tools.ci.delivery.pipeline",
        "tools.ci.python_test_gate",
        "PIL.Image",
        "ethos.adapters.repo.runtime.materialization.input_resolution",
        "ethos.adapters.repo.runtime.materialization.node_package_supply",
    }.intersection(result.stdout.splitlines())


@pytest.mark.parametrize(
    ("state", "explicit", "fails"),
    [
        ("invalid", False, True),
        ("invalid", True, True),
        ("valid", False, False),
        ("valid", True, False),
        ("missing", True, True),
        ("deleted", False, False),
        ("deleted", True, True),
        ("untracked", False, True),
        ("ignored", False, False),
        ("external", False, False),
        ("external", True, True),
    ],
)
def test_config_selection_keeps_native_failures_and_ownership(
    tmp_path, monkeypatch, state, explicit, fails
):
    """Default discovery covers candidates; explicit absent or foreign inputs cannot pass."""
    root = init_git_repo(tmp_path / "repo")
    policy = root / ".config/checks/format/selection.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    relative = "openspec/config.yaml" if state == "external" else ".config/new-policy.yaml"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\nvalue: true\n" if state == "valid" else "broken: [\n")
    (root / ".gitignore").write_text(
        policy.relative_to(root).as_posix() + "\n" + (relative if state == "ignored" else "")
    )
    if state not in {"ignored", "untracked", "missing"}:
        git(root, "add", relative)
    if state in {"missing", "deleted"}:
        target.unlink()
    monkeypatch.setattr(config_quality, "ROOT", root)
    spellings = (
        (relative, str(target), str(root / ".config" / ".." / relative)) if explicit else (None,)
    )
    for spelling in spellings:
        failures = config_quality.run(
            (spelling,) if spelling else (), node=root / "node", package_supply=root
        )
        assert bool(failures) is fails, failures
        if fails:
            assert relative in "\n".join(failures)
            assert state != "external" or "another owner" in "\n".join(failures)


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing",
        "malformed",
        {"known_first_parti": []},
        {"root": "../outside"},
        {"root": " "},
        {"known_first_party": "not-a-list"},
    ],
)
def test_dependency_runner_consumes_declared_policy(tmp_path, monkeypatch, fault):
    """One executor consumes declared values and refuses invalid policy before execution."""
    policy = tmp_path / ".config/checks/deptry/policy.toml"
    policy.parent.mkdir(parents=True)
    data = tomllib.loads((ROOT / policy.relative_to(tmp_path)).read_text())
    package = data["package"][0]
    package["known_first_party"] = ["declared_fixture", "second_fixture"]
    package.update(fault if isinstance(fault, dict) else {})
    if fault != "missing":
        policy.write_text("[broken" if fault == "malformed" else tomli_w.dumps(data))
    for name, value in {
        "ROOT": tmp_path,
        "OUTPUT": tmp_path / "out.json",
        "SUMMARY": tmp_path / "summary.json",
        "declaration_gaps": list,
        "current_tracked_head": lambda _root: "a" * 40,
    }.items():
        monkeypatch.setattr(dependency_hygiene, name, value)
    session = Mock()
    session.run.side_effect = lambda *_args, **_kwargs: dependency_hygiene.OUTPUT.write_text("[]")
    if fault is not None:
        with pytest.raises((OSError, ValueError)):
            dependency_hygiene.run(session)
        session.run.assert_not_called()
        return
    dependency_hygiene.run(session)
    session.run.assert_called_once()
    session.error.assert_not_called()
    args = session.run.call_args.args
    assert [args[i + 1] for i, arg in enumerate(args) if arg == "--known-first-party"] == (
        package["known_first_party"]
    )
    assert args[args.index("--package-module-name-map") + 1] == ",".join(
        package["package_module_name_map"]
    )
