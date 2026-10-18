"""Quality sessions enforce native selection and execution boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from contextlib import nullcontext
from importlib import import_module
from pathlib import Path
from unittest.mock import Mock

import pytest
import tomli_w

import ethos.adapters.repo.runtime.materialization.native_supply as native_supply
import ethos.repository.policy.schema as schema_owner
from ethos.adapters.process import run_command
from tests.support.governed_repository import PARADIGM_FORMATTERS
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
    validate = Mock(return_value={"verdict": "pass", "schema_count": 1, "required_gaps": []})
    monkeypatch.setattr(schema_owner, "schema_validation_report", validate)
    session = Mock()
    sessions.schemas(session)
    validate.assert_called_once_with(sessions.ROOT)
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
    assert registry["markdown-lint"]["command"] == ["{python}", "-m", "nox", "-s", "markdown_lint"]
    assert registry["markdown-lint"]["execution_mode"] == "adapter"
    assert registry["prose"]["command"][-2:] == ["-s", "prose"]
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
    sessions.prose(session)
    assert calls == [("format", sessions.ROOT)]
    assert native == ["policy.yaml"]
    session.error.assert_not_called()
    assert session.run.call_count == 1
    assert "codespell" in Path(session.run.call_args.args[0]).name


def test_fix_applies_each_common_formatter_in_write_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fix verb rewrites Python, Prettier and taplo carriers that check verifies."""
    calls = []
    monkeypatch.setattr(sessions, "_python_paths", lambda _session: ("src/a.py",))
    monkeypatch.setattr(sessions, "prettier_paths", lambda: ("README.md",))
    monkeypatch.setattr(config_quality, "toml_paths", lambda: (Path("pyproject.toml"),))
    sessions.fix(type("Session", (), {"run": lambda _, *args: calls.append(args)})())
    ruff = sessions.RUNTIME.script("ruff")
    assert calls[0][:3] == (ruff, "check", "--fix")
    assert calls[0][-1] == "src/a.py"
    assert calls[1][:2] == (ruff, "format")
    assert "--check" not in calls[1]
    assert calls[2][-2:] == ("--write", "README.md")
    taplo = ("format", "--config", str(config_quality.TAPLO_CONFIG), "pyproject.toml")
    assert calls[3][-4:] == taplo


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


def test_prose_executor_consumes_only_declared_policy_paths() -> None:
    calls = []
    sessions.prose(type("Session", (), {"run": lambda _, *args: calls.append(args)})())
    expected = [sessions.RUNTIME.script("codespell"), "--toml"]
    expected += [str(ROOT / ".config/checks/codespell/codespell.toml")]
    expected += ["README.md", "CONTRIBUTING.md", "AGENTS.md"]
    assert calls[0] == (*expected, "docs", "rules", "openspec/specs")


@pytest.mark.parametrize(
    ("configuration", "policy", "message"),
    [
        (None, 'paths = ["docs"]\n', "declares no [tool.codespell] table"),
        ("count = true\n", 'paths = ["docs"]\n', "declares no [tool.codespell] table"),
        ("[tool.codespell]\ncount = true\n", None, "prose policy paths are missing"),
    ],
    ids=["missing", "unread", "no-paths"],
)
def test_prose_refuses_configuration_codespell_would_not_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configuration, policy, message
) -> None:
    """A carrier without its table is silently ignored by codespell, so the session refuses it."""
    for name, text in (("CODESPELL_CONFIG", configuration), ("PROSE_POLICY", policy)):
        path = tmp_path / name
        if text is not None:
            path.write_text(text, encoding="utf-8")
        monkeypatch.setattr(sessions, name, path)
    session = Mock()
    session.error.side_effect = SystemExit
    with pytest.raises(SystemExit):
        sessions.prose(session)
    assert message in session.error.call_args.args[0]
    session.run.assert_not_called()


def test_codespell_reads_its_declared_configuration(tmp_path: Path) -> None:
    """The count the carrier enables appears although no count option is passed."""
    sample = tmp_path / "sample.md"
    sample.write_text("teh sample\n", encoding="utf-8")
    command = (sessions.RUNTIME.script("codespell"), "--toml", str(sessions.CODESPELL_CONFIG))
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
    ("state", "explicit", "fails"),
    [
        ("invalid", False, True),
        ("invalid", True, True),
        ("valid", False, False),
        ("valid", True, False),
        ("scalar", True, False),
        ("blank", True, True),
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
    # The fixture's TOML formatter bindings are not this YAML selection case's subject.
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    relative = "openspec/config.yaml" if state == "external" else ".config/new-policy.yaml"
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        {
            "valid": "---\nvalue: true\n",
            "scalar": "---\nvalue: |\n  first\n\n\n  second\n",
            "blank": "---\nfirst: 1\n\n\nsecond: 2\n",
        }.get(state, "broken: [\n")
    )
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


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("state", ["valid", "malformed", "missing"])
def test_native_configuration_compiles_declared_vale_vocabulary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, *, explicit: bool
) -> None:
    """The real locked parser rejects bad or absent inputs without rewriting them."""
    root = init_git_repo(tmp_path / "repo")
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    (root / ".gitignore").write_text(policy.relative_to(root).as_posix() + "\n")
    config = root / ".config/checks/vale/vale.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[DEFAULT]\nStylesPath = styles\nVocab = Common\nMinAlertLevel = error\n"
        "\n[*.md]\nBasedOnStyles = Vale\n"
    )
    vocabulary = config.parent / "styles/config/vocabularies/Common"
    vocabulary.mkdir(parents=True)
    accepted, rejected = vocabulary / "accept.txt", vocabulary / "reject.txt"
    accepted.write_text("(?i:invalid\n" if state == "malformed" else "(?i:prewrite)\n")
    rejected.write_text("Github\n")
    inputs = (config, accepted, rejected)
    git(root, "add", *(str(path.relative_to(root)) for path in inputs))
    if state == "missing":
        accepted.unlink()
    original = {path: path.read_bytes() for path in inputs if path.exists()}
    monkeypatch.setattr(config_quality, "ROOT", root)

    failures = config_quality.run(
        (str(accepted.relative_to(root)),) if explicit else (),
        node=root / "unselected-node",
        package_supply=root,
    )

    assert bool(failures) is (state != "valid"), failures
    if state == "malformed":
        assert "E100" in "\n".join(failures)
    if state == "missing":
        assert "accept" in "\n".join(failures)
    assert {path: path.read_bytes() for path in original} == original
    assert accepted.exists() is (state != "missing")
    assert not (root / "build").exists()


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("content", ["prewrite\n", "(?i:invalid\n"], ids=["valid", "malformed"])
def test_configuration_refuses_vocabulary_without_native_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str, *, explicit: bool
) -> None:
    """Owned vocabulary inputs cannot pass through an unrelated native selection."""
    root = init_git_repo(tmp_path / "repo")
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    (root / ".gitignore").write_text(policy.relative_to(root).as_posix() + "\n")
    config = root / ".config/checks/vale/vale.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[DEFAULT]\nStylesPath = styles\nVocab = Common\nMinAlertLevel = error\n"
        "\n[*.md]\nBasedOnStyles = Vale\n"
    )
    selected = config.parent / "styles/config/vocabularies/Common/accept.txt"
    selected.parent.mkdir(parents=True)
    selected.write_text("prewrite\n")
    unselected = config.parent / "styles/config/vocabularies/Unselected/accept.txt"
    unselected.parent.mkdir(parents=True)
    unselected.write_text(content)
    inputs = (config, selected, unselected)
    git(root, "add", *(str(path.relative_to(root)) for path in inputs))
    original = {path: path.read_bytes() for path in inputs}
    monkeypatch.setattr(config_quality, "ROOT", root)

    failures = config_quality.run(
        (str(unselected.relative_to(root)),) if explicit else (),
        node=root / "unselected-node",
        package_supply=root,
    )

    assert failures, "The native configuration never consumed the selected vocabulary."
    assert str(unselected.relative_to(root)) in "\n".join(failures)
    assert "not consumed" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (selected.parent / "reject.txt").exists()
    assert not (root / "build").exists()


@pytest.mark.parametrize("state", ["valid", "malformed"])
@pytest.mark.parametrize("default_vocabulary", [False, True])
def test_native_configuration_compiles_section_vocabulary_without_optional_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, *, default_vocabulary: bool
) -> None:
    """Section-selected vocabulary is compiled without inventing optional inputs."""
    root = init_git_repo(tmp_path / "repo")
    git(root, "rm", "-q", *PARADIGM_FORMATTERS)
    policy = root / ".config/checks/format-selection/policy.toml"
    policy.parent.mkdir(parents=True)
    policy.write_bytes((ROOT / policy.relative_to(root)).read_bytes())
    (root / ".gitignore").write_text(policy.relative_to(root).as_posix() + "\n")
    config = root / ".config/checks/vale/vale.ini"
    config.parent.mkdir(parents=True)
    config.write_text(
        "[DEFAULT]\nStylesPath = styles\n"
        + ("Vocab = Common\n" if default_vocabulary else "")
        + "MinAlertLevel = error\n"
        "\n[*.md]\nBasedOnStyles = Vale\n\n[docs/*.md]\nVocab = Additional\n"
    )
    common = config.parent / "styles/config/vocabularies/Common/accept.txt"
    common.parent.mkdir(parents=True)
    common.write_text("prewrite\n")
    additional = config.parent / "styles/config/vocabularies/Additional/accept.txt"
    additional.parent.mkdir(parents=True)
    additional.write_text("(?i:invalid\n" if state == "malformed" else "semantics\n")
    inputs = (config, common, additional)
    git(root, "add", *(str(path.relative_to(root)) for path in inputs))
    original = {path: path.read_bytes() for path in inputs}
    monkeypatch.setattr(config_quality, "ROOT", root)

    failures = config_quality.run(
        (str(additional.relative_to(root)),), node=root / "unselected-node", package_supply=root
    )

    assert bool(failures) is (state == "malformed"), failures
    if failures:
        assert "E100" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (common.parent / "reject.txt").exists()
    assert not (additional.parent / "reject.txt").exists()
    assert not (root / "build").exists()
