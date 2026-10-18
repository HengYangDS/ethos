"""Quality sessions enforce native selection and execution boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest
import tomli_w

import ethos.adapters.gates.configuration as configuration_gate
import ethos.adapters.repo.runtime.materialization.native_supply as native_supply
import ethos.repository.policy.schema as schema_owner
from ethos.adapters.process import run_command
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.normalization.coercion import string_sequence
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
    assert all(
        callable(sessions.SESSION_IMPLEMENTATIONS.get(name) or getattr(sessions, name))
        for name in public
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
    validate = Mock(return_value={"verdict": "pass", "schema_count": 1, "required_gaps": []})
    monkeypatch.setattr(schema_owner, "schema_validation_report", validate)
    session = Mock()
    sessions.schemas(session)
    validate.assert_called_once_with(sessions.ROOT)
    session.log.assert_called_once()
    session.run.assert_not_called()
    session.error.assert_not_called()


def test_fix_projects_authorized_native_source_format_with_current_head() -> None:
    """The source fix verb forwards exact inputs to the one fresh native write owner."""
    head = "a" * 40
    session = Mock(posargs=["source file.py"])
    session.run.side_effect = [head + "\n", None]

    sessions.fix(session)

    observed, applied = session.run.call_args_list
    assert observed.args == ("git", "rev-parse", "HEAD")
    assert applied.args == (
        str(sessions.RUNTIME.python),
        "-B",
        "-m",
        "ethos.cli",
        "lane",
        "format",
        "--root",
        str(ROOT),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "source file.py",
        "--json",
    )


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


def test_prose_executor_reuses_installed_native_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source Nox projects the product owner without a competing spelling command."""
    owner = sessions.import_module("ethos.adapters.gates.tool")
    provider = Mock(return_value={"verdict": "pass"})
    monkeypatch.setattr(owner, "prose_report", provider)
    session = Mock()
    sessions.prose(session)
    provider.assert_called_once_with(ROOT)
    session.log.assert_called_once()
    session.run.assert_not_called()
    session.error.assert_not_called()


def test_configuration_gate_has_one_installed_owner() -> None:
    """Native configuration checks cannot require the ETHOS source Nox toolchain."""
    gate = load_gate_registry_declaration().registry()["config-quality"]
    assert gate.providers == ("ethos.adapters.gates.configuration:configuration_report",)
    assert not gate.command
    assert not (ROOT / "tools/ci/config_quality.py").exists()


@pytest.mark.parametrize("checking", [False, True])
def test_source_format_sessions_project_one_native_owner(*, checking: bool) -> None:
    """Check and fix share exact literal inputs without a second Nox formatter."""
    session = Mock(posargs=["source file.py"])
    operation = sessions.format_check if checking else sessions.source_format
    operation(session)
    command = tuple(session.run.call_args.args)
    assert command[:5] == (str(sessions.RUNTIME.python), "-B", "-m", "ethos.cli", "lane")
    assert command[5:8] == ("format", "--root", str(ROOT))
    assert "source file.py" in command
    assert ("--check" in command) is checking
    assert "--apply" not in command
    assert "--authorize" not in command
    session.run.assert_called_once()


def test_source_format_gate_is_supplied_by_the_installed_product() -> None:
    declaration = load_gate_registry_declaration()
    gate = declaration.registry()["source-format"]
    assert gate.providers == ("ethos.adapters.gates.formatting:source_format_report",)
    assert gate.command == ()
    assert gate.writes_files is False
    assert gate.required_for_paths
    assert "source-format" in declaration.proof_sets.default
    assert "source-format" in declaration.proof_sets.full


def test_configuration_owner_preserves_the_common_floor_and_exact_inputs(tmp_path) -> None:
    """Local ignores and ambient configuration cannot weaken installed native checks."""
    root = init_git_repo(tmp_path / "repo")
    yaml_policy = root / ".config/checks/yamllint/.yamllint.yaml"
    yaml_policy.parent.mkdir(parents=True)
    yaml_policy.write_text("---\nextends: default\nignore: '*.yaml'\n")
    yaml_input = root / "example.yaml"
    toml_input = root / "example.toml"
    json_input = root / "example.json"
    ini_input = root / "example.ini"
    git(root, "add", yaml_policy.relative_to(root).as_posix())
    cases = (
        (yaml_input, "---\nvalue: true\n", "pass"),
        (yaml_input, "---\nvalue: true\n\n\nother: 1\n", "block"),
        (toml_input, 'value = "valid"\n', "pass"),
        (toml_input, 'value="valid"\n', "block"),
        (json_input, '{\n  "value": true\n}\n', "pass"),
        (json_input, '{"value":true}\n', "block"),
        (ini_input, "[native]\nvalue = valid\n", "pass"),
        (ini_input, "[native]\nvalue = first\nvalue = duplicate\n", "block"),
    )
    for target, content, verdict in cases:
        target.write_text(content)
        report = configuration_gate.configuration_report(root, paths=(target.name,))
        assert (report["verdict"], target.read_text()) == (verdict, content), report
    invalid_policy = "rules:\n  missing-native-rule: enable\n"
    yaml_policy.write_text(invalid_policy)
    yaml_input.write_text("---\nvalue: true\n")
    report = configuration_gate.configuration_report(root, paths=(yaml_input.name,))
    assert report["verdict"] == "block", report
    assert report["required_gaps"]
    assert yaml_policy.read_text() == invalid_policy
    assert yaml_input.read_text() == "---\nvalue: true\n"


def test_configuration_owner_validates_native_formatter_policy_before_checking(tmp_path) -> None:
    """Original formatter rejects malformed native policy and preserves authored bytes."""
    root = init_git_repo(tmp_path / "repo")
    target = root / "example.json"
    content = '{\n  "value": true\n}\n'
    target.write_text(content)
    policy = root / ".config/checks/prettier/prettier.toml"
    policy.parent.mkdir(parents=True, exist_ok=True)
    git(root, "add", target.name)
    for declaration, verdict in (
        ({"tabWidth": 2}, "pass"),
        ({"tabWidth": "unknown"}, "block"),
        ({"tabWidth": True}, "block"),
        ({"unknownFormat": True}, "block"),
    ):
        original = tomli_w.dumps(declaration)
        policy.write_text(original)
        git(root, "add", policy.relative_to(root).as_posix())
        report = configuration_gate.configuration_report(root, paths=(target.name,))
        assert (report["verdict"], target.read_text(), policy.read_text()) == (
            verdict,
            content,
            original,
        ), report
        assert bool(report["required_gaps"]) == (verdict == "block"), report


@pytest.mark.parametrize("configuration", ["count = true\n", "[tool]\ncount = true\n"])
def test_prose_refuses_configuration_codespell_would_not_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configuration: str
) -> None:
    """The shared provider refuses a silently ignored table before native execution."""
    root = init_git_repo(tmp_path / "repo")
    sample = root / "README.md"
    sample.write_text("# Valid native prose\n", encoding="utf-8")
    git(root, "add", sample.name)
    config = tmp_path / "codespell.toml"
    config.write_text(configuration, encoding="utf-8")
    owner = sessions.import_module("ethos.adapters.gates.tool")
    monkeypatch.setattr(owner, "native_configurations", lambda *_args: (str(config),))
    execution = Mock(return_value={"verdict": "pass", "stderr": "0", "required_gaps": []})
    monkeypatch.setattr(owner, "quality_tool_report", execution)

    report = owner.prose_report(root)

    assert report["verdict"] == "block", report
    assert report["required_gaps"] == [f"codespell_configuration_table_missing:{config}"]
    execution.assert_not_called()
    assert (sample.read_text(), config.read_text()) == (
        "# Valid native prose\n",
        configuration,
    )


def test_codespell_reads_its_declared_configuration(tmp_path: Path) -> None:
    """The count the carrier enables appears although no count option is passed."""
    sample = tmp_path / "sample.md"
    sample.write_text("teh sample\n", encoding="utf-8")
    config = ROOT / ".config/checks/codespell/codespell.toml"
    command = (sessions.RUNTIME.script("codespell"), "--toml", str(config))
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
def test_config_selection_keeps_native_failures_and_ownership(tmp_path, state, explicit, fails):
    """Default discovery covers candidates; explicit absent or foreign inputs cannot pass."""
    root = init_git_repo(tmp_path / "repo")
    (root / ".config").mkdir(exist_ok=True)
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
    (root / ".gitignore").write_text(relative if state == "ignored" else "")
    if state not in {"ignored", "untracked", "missing"}:
        git(root, "add", relative)
    if state in {"missing", "deleted"}:
        target.unlink()
    spellings = (
        (relative, str(target), str(root / ".config" / ".." / relative)) if explicit else (None,)
    )
    for spelling in spellings:
        report = configuration_gate.configuration_report(
            root, paths=(spelling,) if spelling else ()
        )
        failures = string_sequence(report["required_gaps"])
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
    tmp_path: Path, state: str, *, explicit: bool
) -> None:
    """The real locked parser rejects bad or absent inputs without rewriting them."""
    root = init_git_repo(tmp_path / "repo")
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

    report = configuration_gate.configuration_report(
        root, paths=(str(accepted.relative_to(root)),) if explicit else ()
    )
    failures = string_sequence(report["required_gaps"])

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
    tmp_path: Path, content: str, *, explicit: bool
) -> None:
    """Owned vocabulary inputs cannot pass through an unrelated native selection."""
    root = init_git_repo(tmp_path / "repo")
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

    report = configuration_gate.configuration_report(
        root, paths=(str(unselected.relative_to(root)),) if explicit else ()
    )
    failures = string_sequence(report["required_gaps"])

    assert failures, "The native configuration never consumed the selected vocabulary."
    assert str(unselected.relative_to(root)) in "\n".join(failures)
    assert "not consumed" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (selected.parent / "reject.txt").exists()
    assert not (root / "build").exists()


@pytest.mark.parametrize("state", ["valid", "malformed"])
@pytest.mark.parametrize("default_vocabulary", [False, True])
def test_native_configuration_compiles_section_vocabulary_without_optional_files(
    tmp_path: Path, state: str, *, default_vocabulary: bool
) -> None:
    """Section-selected vocabulary is compiled without inventing optional inputs."""
    root = init_git_repo(tmp_path / "repo")
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

    report = configuration_gate.configuration_report(
        root, paths=(str(additional.relative_to(root)),)
    )
    failures = string_sequence(report["required_gaps"])

    assert bool(failures) is (state == "malformed"), failures
    if failures:
        assert "E100" in "\n".join(failures)
    assert {path: path.read_bytes() for path in inputs} == original
    assert not (common.parent / "reject.txt").exists()
    assert not (additional.parent / "reject.txt").exists()
    assert not (root / "build").exists()
