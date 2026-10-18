"""Quality sessions enforce native selection and execution boundaries."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tomllib
from contextlib import nullcontext
from importlib import import_module
from pathlib import Path
from unittest.mock import Mock

import pytest
import tomli_w

import ethos.adapters.gates.tool as quality_tools
import ethos.adapters.repo.content.observation as content_observation
import ethos.adapters.repo.runtime.materialization.native_supply as native_supply
import ethos.repository.policy.schema as schema_owner
import tools.ci.local_ci as local_ci
from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.release.resources import canonical_resource
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
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


def test_package_lifecycle_has_one_execution_owner() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}
    lifecycle_gates = {
        gate["id"]
        for gate in declaration["gates"]
        if "installability" in gate.get("dimensions", [])
    }

    assert lifecycle_gates == {"local-install-smoke"}
    assert full.index("build") < full.index("local-install-smoke")
    assert gates["unit-architecture"]["depends_on"][0] == "build"
    assert set(gates["local-install-smoke"]["depends_on"]) == {
        "build",
        "dependency-vulnerabilities",
    }
    assert "coverage-floor" in full
    assert gates["coverage-floor"]["depends_on"] == ["unit-architecture"]
    assert "local-install-smoke" not in declaration["proof_sets"]["default"]
    assert gates["unit-architecture"]["resource_locks"]["artifacts/python"] == "shared"
    assert gates["local-install-smoke"]["network_policy"] == "offline"
    assert gates["local-install-smoke"]["writes_files"] is True
    expected = resolve_gate_policy(ROOT, full=True)
    assert local_ci.owner_commands() == [
        shlex.join(gate_execution_identity(expected.registry[node.id])) for node in expected.nodes
    ]
    assert expected.gate_ids.count("local-install-smoke") == 1
    assert not expected.registry["unit-architecture"].conflicts_with(
        expected.registry["local-install-smoke"]
    )
    assert expected.registry["generated-artifacts"].conflicts_with(
        expected.registry["local-install-smoke"]
    )


def test_project_runtime_is_the_only_executable_resolution_owner() -> None:
    consumers = (
        "tools/ci/sessions.py",
        "tools/ci/dependency_hygiene.py",
        "tools/ci/delivery/acceptance/effect.py",
        "tools/ci/delivery/pipeline.py",
    )
    for relative in consumers:
        assert "tools.ci.toolchain.environment" in (ROOT / relative).read_text(encoding="utf-8")


def test_pytest_process_environment_is_hermetic() -> None:
    count = int(os.environ["GIT_CONFIG_COUNT"])
    entries = tuple(
        (os.environ[f"GIT_CONFIG_KEY_{index}"], os.environ[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    )

    assert ("core.fsmonitor", "false") in entries
    assert len([key for key, _value in entries if key == "init.templateDir"]) == 1
    assert not {"user.name", "user.email"} & {key for key, _value in entries}
    assert all(value for _key, value in entries)
    for role in ("AUTHOR", "COMMITTER"):
        assert os.environ[f"GIT_{role}_NAME"] == "ETHOS Test"
        assert os.environ[f"GIT_{role}_EMAIL"] == "test@example.invalid"
    assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    assert os.environ["GIT_TERMINAL_PROMPT"] == "0"
    assert (os.environ["OPENSPEC_TELEMETRY"], os.environ["OPENSPEC_NO_UPDATE_CHECK"]) == ("0", "1")


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
    origins = Mock()
    observe = Mock(return_value=origins)
    validate = Mock(return_value={"verdict": "pass", "schema_count": 1, "required_gaps": []})
    monkeypatch.setattr(content_observation, "observed_document_origins", observe)
    monkeypatch.setattr(schema_owner, "schema_validation_report", validate)
    session = Mock()
    sessions.schemas(session)
    observe.assert_called_once_with(sessions.ROOT)
    validate.assert_called_once_with(sessions.ROOT, retained_origins=origins)
    session.log.assert_called_once()
    session.run.assert_not_called()
    session.error.assert_not_called()


def test_native_document_sessions_reuse_product_report_owners(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nox transports the shared reports; YAML and original spelling selection stay covered."""
    registry = {
        item["id"]: item
        for item in tomllib.loads((ROOT / "system/gates.toml").read_text())["gates"]
    }
    assert registry["markdown-lint"]["providers"] == [
        "ethos.adapters.gates.markdown:markdown_format_report"
    ]
    assert registry["markdown-lint"]["execution_mode"] == "provider"
    assert registry["prose"]["providers"] == ["ethos.adapters.gates.tool:prose_report"]
    assert registry["prose"]["execution_mode"] == "provider"
    calls = []
    report = {"verdict": "pass", "required_gaps": []}
    monkeypatch.setattr(
        import_module("ethos.adapters.gates.markdown"),
        "working_document_report",
        lambda root, *, kind: calls.append((kind, root)) or report,
    )
    monkeypatch.setattr(sessions, "prettier_paths", lambda: ("guide.md", "policy.yaml"))
    native = []
    monkeypatch.setattr(sessions, "_prettier", lambda _session, *paths: native.extend(paths))
    session = Mock()
    sessions.markdown_lint(session)
    assert calls == [("format", sessions.ROOT)]
    assert native == ["policy.yaml"]
    session.error.assert_not_called()
    session.run.assert_not_called()


@pytest.mark.parametrize("verdict", ["pass", "block"])
def test_prose_session_uses_the_shared_native_owner(monkeypatch, verdict: str) -> None:
    """Nox projects the product result without restating policy or native execution."""
    provider = Mock(
        return_value={
            "verdict": verdict,
            "required_gaps": [] if verdict == "pass" else ["spelling"],
        }
    )
    monkeypatch.setattr(quality_tools, "prose_report", provider)
    session = Mock()
    sessions.prose(session)
    provider.assert_called_once_with(sessions.ROOT)
    session.run.assert_not_called()
    assert session.error.called == (verdict == "block")


def test_full_test_session_refuses_selectors_before_loading_supply(tmp_path) -> None:
    """A focused request must not silently start the complete proof floor."""
    result = run_command(
        ROOT,
        (
            sys.executable,
            "-B",
            "-m",
            "nox",
            "-s",
            "tests",
            "--",
            str(Path(__file__).relative_to(ROOT)),
        ),
        env={"ETHOS_NODE_PACKAGE_SUPPLY": str(tmp_path / "missing")},
        timeout=30,
    )
    assert result.returncode != 0
    assert "tests_session_selection_not_supported" in result.stderr
    assert "node_package_supply_unavailable" not in result.stderr


def test_fix_applies_each_common_formatter_in_write_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The native fix writes Python, Markdown and TOML with the same shared policies."""
    root = init_git_repo(tmp_path / "repo")
    ruff = root / ".config/checks/ruff/ruff.toml"
    ruff.parent.mkdir(parents=True, exist_ok=True)
    ruff.write_bytes((ROOT / ruff.relative_to(root)).read_bytes())
    inputs = {
        "sample.py": '"""Native formatter fixture."""\n\nanswer=42\n',
        "README.md": "#   Guide\n",
        "pyproject.toml": '[project]\nname= "example"\n',
    }
    for relative, text in inputs.items():
        (root / relative).write_text(text)
    git(root, "add", "--all")
    monkeypatch.setattr(sessions, "ROOT", root)
    monkeypatch.setattr(sessions, "RUFF_CACHE", tmp_path / "ruff-cache")
    calls = []

    def execute(_session, *args, **kwargs):
        calls.append(args)
        kwargs.pop("silent", None)
        return run_command(root, args, timeout=60, check=True, **kwargs).stdout

    sessions.fix(type("Session", (), {"run": execute})())

    assert (root / "sample.py").read_text() == '"""Native formatter fixture."""\n\nanswer = 42\n'
    assert (root / "README.md").read_text() == "# Guide\n"
    assert (root / "pyproject.toml").read_text() == '[project]\nname = "example"\n'
    original = {relative: (root / relative).read_bytes() for relative in inputs}
    sessions.fix(type("Session", (), {"run": execute})())
    assert {relative: (root / relative).read_bytes() for relative in inputs} == original
    ruff_commands = [args for args in calls if Path(args[0]).name == "ruff"]
    assert ruff_commands[0][1:3] == ("check", "--fix")
    assert ruff_commands[1][1] == "format"
    assert not any("--check" in command for command in ruff_commands)


def test_secrets_scans_a_mirror_of_only_the_tracked_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignored and untracked files stay outside the scan; tracked links stay links."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (repo / "notes.txt").write_text("tracked\n", encoding="utf-8")
    (repo / "notes-link.txt").symlink_to("notes.txt")
    git(repo, "add", ".gitignore", "notes.txt", "notes-link.txt")
    (repo / "local.log").write_text("ignored\n", encoding="utf-8")
    (repo / "draft.txt").write_text("untracked\n", encoding="utf-8")
    supply = tmp_path / "supply"
    supply.mkdir()
    (supply / "gitleaks").write_text("", encoding="utf-8")
    (supply / "gitleaks").chmod(0o755)
    monkeypatch.setattr(native_supply, "materialize_tool", lambda _root, _name: supply)
    monkeypatch.setattr(sessions, "ROOT", repo)
    observed: list[tuple[tuple[str, ...], list[str], bool]] = []

    def run(_session: object, *args: str) -> None:
        mirror = Path(args[2])
        listed = sorted(
            path.relative_to(mirror).as_posix()
            for path in mirror.rglob("*")
            if path.is_file() or path.is_symlink()
        )
        observed.append((args, listed, (mirror / "notes-link.txt").is_symlink()))

    sessions.secrets(type("Session", (), {"run": run})())
    [(args, listed, linked)] = observed
    assert listed == sorted(git(repo, "ls-files").splitlines())
    assert {"notes.txt", "notes-link.txt"} <= set(listed)
    assert not {"local.log", "draft.txt"} & set(listed)
    assert linked
    report = repo / "build/evidence/quality/secrets/report.json"
    assert args[0] == str(supply / "gitleaks")
    assert args[1] == "dir"
    assert args[3:] == (
        "--config",
        str(sessions.GITLEAKS_CONFIG),
        "--redact",
        "--report-format",
        "json",
        "--report-path",
        str(report),
    )
    assert report.parent.is_dir()


@pytest.mark.parametrize(
    ("state", "message"),
    [
        ("absent-table", "native_prose_configuration_invalid"),
        ("unread", "native_prose_configuration_invalid"),
        ("malformed", "native_prose_configuration_invalid"),
        ("deleted", "native_tool_configuration_invalid:codespell"),
    ],
)
def test_prose_refuses_configuration_codespell_would_not_read(
    tmp_path: Path, state: str, message: str
) -> None:
    """The shared native consumer refuses unavailable or silently ignored declarations."""
    root = init_git_repo(tmp_path / "repo")
    config = root / ".config/checks/codespell/codespell.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("[tool.codespell]\ncount = true\n")
    git(root, "add", str(config.relative_to(root)))
    if state == "deleted":
        config.unlink()
    else:
        config.write_text(
            "[broken"
            if state == "malformed"
            else "[tool]\n"
            if state == "unread"
            else "count = true\n"
        )
    original = config.read_bytes() if config.exists() else None

    report = quality_tools.prose_report(root)

    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert any(message in gap for gap in gaps), report
    assert (config.read_bytes() if config.exists() else None) == original


def test_codespell_reads_its_declared_configuration(tmp_path: Path) -> None:
    """The count the carrier enables appears although no count option is passed."""
    sample = tmp_path / "sample.md"
    sample.write_text("teh sample\n", encoding="utf-8")
    command = (
        sessions.RUNTIME.script("codespell"),
        "--toml",
        str(canonical_resource(".config/checks/codespell/codespell.toml")),
    )
    result = run_command(tmp_path, (*command, str(sample)), timeout=60)
    assert result.returncode != 0
    assert "teh ==> the" in result.stdout
    assert result.stderr.strip().splitlines()[-1] == "1"


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
    "fault",
    [
        None,
        "missing",
        "malformed",
        {"known_first_parti": []},
        {"root": "../outside"},
        {"root": " "},
        {"known_first_party": "not-a-list"},
        (None, 0, "unknown", "unobservable"),
        ("{", 0, "unknown", "unobservable"),
        ("{}", 0, "unknown", "unobservable"),
        ("[{}]", 0, "block", "findings_reported"),
        ("[{}]", 1, "block", "findings_reported"),
        ("[]", 1, "block", "execution_failed"),
        ("[]", 2, "block", "execution_failed"),
        (None, 2, "block", "execution_failed"),
        (None, "spawn", "unknown", "execution_unavailable"),
        (None, "timeout", "unknown", "execution_unavailable"),
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
    outcome = fault if isinstance(fault, tuple) else ("[]", 0, "pass", "passed")
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

    def execute(_root, command, **kwargs):
        assert kwargs["timeout"] > 0
        if outcome[1] == "spawn":
            message = "missing deptry"
            raise FileNotFoundError(message)
        if outcome[1] == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], stderr=b"partial error")
        if outcome[0] is not None:
            dependency_hygiene.OUTPUT.write_text(outcome[0])
        return subprocess.CompletedProcess(command, outcome[1], "native stdout", "native stderr")

    transport = Mock(side_effect=execute)
    monkeypatch.setattr(dependency_hygiene, "run_command", transport, raising=False)
    if fault is not None and not isinstance(fault, tuple):
        with pytest.raises((OSError, ValueError)):
            dependency_hygiene.run(session)
        transport.assert_not_called()
        return
    dependency_hygiene.run(session)
    transport.assert_called_once()
    report = json.loads(dependency_hygiene.SUMMARY.read_text())
    assert (report["verdict"], report["state"]) == outcome[2:]
    assert report["exit_code"] == (outcome[1] if isinstance(outcome[1], int) else None)
    assert report["stderr"]
    assert session.error.called == (outcome[2] != "pass")
    args = transport.call_args.args[1]
    assert [args[i + 1] for i, arg in enumerate(args) if arg == "--known-first-party"] == (
        package["known_first_party"]
    )
    assert args[args.index("--package-module-name-map") + 1] == ",".join(
        package["package_module_name_map"]
    )


@pytest.mark.parametrize("code", [0, 19])
def test_javascript_gate_executes_package_behavior(tmp_path, monkeypatch, code):
    """Native package failure propagates, and both outcomes reclaim owned state."""
    registry = tomllib.loads((ROOT / "system/gates.toml").read_text())
    assert "javascript-tests" in registry["proof_sets"]["full"]
    body = "require('node:fs').writeFileSync('node.txt', process.execPath);"
    script = f'node -e "{body}process.exit({code})"'
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"test:npm": script}}))
    monkeypatch.setattr(sessions, "ROOT", tmp_path)
    session = Mock()
    session.run.side_effect = lambda *args, env: run_command(
        tmp_path, args, env=env, timeout=30, check=True
    )
    with pytest.raises(subprocess.CalledProcessError) if code else nullcontext():
        sessions.javascript_tests(session)
    session.run.assert_called_once()
    assert (tmp_path / "node.txt").read_text() == str(sessions.RUNTIME.node_executable())
    assert not Path(session.run.call_args.kwargs["env"]["npm_config_cache"]).exists()
