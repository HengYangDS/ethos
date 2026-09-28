"""Qualify native code quality through public adopter proof, not command success."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.toolchain.mise as native_mise
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo


def _declare_quality_profile(repo: Path, gate_owner: str) -> None:
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    header = 'profile_id = "native-quality-adopter"\n\n[openspec]\nmaterial_paths = ["**"]\n\n'
    if gate_owner == "profile":
        profile.write_text(
            header + '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
            '[proof.code_correctness_map]\nbehavior = "behavior"\n'
            'static-analysis = "static"\n\n'
            '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
            'providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n\n'
            '[[proof.gates]]\nid = "static"\nkind = "lint"\n'
            'providers = ["ethos.adapters.gates.code_quality:static_report"]\n',
            encoding="utf-8",
        )
        return
    profile.write_text(header + '[proof]\ngate_registry = "system/gates.toml"\n', encoding="utf-8")
    registry = repo / "system/gates.toml"
    registry.parent.mkdir()
    registry.write_text(
        'schema_version = 1\nid = "native-quality"\n\n'
        '[proof_sets]\ndefault = ["behavior", "static"]\n'
        'full = ["behavior", "static"]\n\n'
        '[[gates]]\nid = "behavior"\nkind = "test"\n'
        'profile = "repository"\nexecution_mode = "provider"\n'
        'tool_adapter = "ethos"\n'
        'providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n\n'
        '[[gates]]\nid = "static"\nkind = "lint"\n'
        'profile = "repository"\nexecution_mode = "provider"\n'
        'tool_adapter = "ethos"\n'
        'providers = ["ethos.adapters.gates.code_quality:static_report"]\n',
        encoding="utf-8",
    )


def _write_go_fixture(repo: Path, defect: str) -> None:
    (repo / "go.mod").write_text("module example.invalid/quality\n\ngo 1.26\n")
    (repo / "answer.go").write_text(
        "package quality\n\nfunc Answer() int { return 42 }\n"
        if defect != "syntax"
        else "package quality\n\nfunc Answer( {\n"
    )
    if defect == "same-name":
        (repo / "sub").mkdir()
        (repo / "sub/answer.go").write_text("package sub\n\nfunc Answer() int { return 42 }\n")
        test = (
            'package quality\n\nimport ("testing"; "example.invalid/quality/sub")\n\n'
            'func TestAnswer(t *testing.T) { if sub.Answer() != 42 { t.Fatal("wrong") } }\n'
        )
    else:
        test = (
            'package quality\n\nimport "testing"\n\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n'
        )
    (repo / "answer_test.go").write_text(test)
    if defect == "unexercised":
        (repo / "unused.go").write_text("package quality\n\nfunc Unused() int { return 0 }\n")
    if defect != "syntax":
        sources = ["answer.go", "answer_test.go"]
        sources.extend(path for path in ("unused.go", "sub/answer.go") if (repo / path).is_file())
        subprocess.run(["gofmt", "-w", *sources], cwd=repo, check=True)


def _write_javascript_fixture(repo: Path, defect: str) -> None:
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text(
        "export function answer() { return 42; }\n"
        if defect != "syntax"
        else "export function answer( {\n"
    )
    if defect == "same-name":
        (repo / "sub").mkdir()
        (repo / "sub/answer.js").write_text("export function answer() { return 42; }\n")
    imported = "./sub/answer.js" if defect == "same-name" else "./answer.js"
    (repo / "answer.test.js").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        f'import {{answer}} from "{imported}";\n'
        'test("answer", () => assert.equal(answer(), 42));\n'
    )
    if defect == "unexercised":
        (repo / "unused.js").write_text("export function unused() { return 0; }\n")


def test_failed_native_go_check_retains_actionable_process_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed provider must retain the native failure, not only a generic gap."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.26\n",
            "answer.go": "package quality\nfunc Answer() int { return 41 }\n",
            "answer_test.go": 'package quality\nimport "testing"\nfunc TestAnswer(t *testing.T) { '
            'if Answer() != 42 { t.Fatal("wrong answer") } }\n',
        },
    )
    monkeypatch.setattr(native_quality, "_executable", lambda _root, name: name)
    monkeypatch.setattr(
        native_quality,
        "_go_package_sources",
        lambda _root, _production, _native: {"example.invalid/quality/answer.go": "answer.go"},
    )

    def fail_command(root: Path, command: tuple[str, ...], **_kwargs: object):
        assert root == repo
        return subprocess.CompletedProcess(
            command,
            1,
            '{"Action":"output","Test":"TestAnswer","Output":"wrong answer\\n"}\n'
            '{"Action":"fail","Test":"TestAnswer"}\n',
            "go test: exit status 1",
        )

    monkeypatch.setattr(native_quality, "run_command", fail_command)
    report = native_quality.behavior_report(repo)

    assert report["required_gaps"] == ["quality_behavior_go_tests_failed"]
    diagnostics = report["diagnostics"]
    assert isinstance(diagnostics, list)
    failure = diagnostics[0]
    assert failure["code"] == "go_tests_failed"
    assert failure["cwd"] == str(repo)
    assert failure["command"][:2] == ["go", "test"]
    assert failure["observation"]["exit_code"] == 1
    assert "wrong answer" in failure["observation"]["stdout_tail"]
    assert failure["cause"] == "go test: exit status 1"


def test_public_adopter_proof_reports_native_go_test_failure(tmp_path: Path) -> None:
    """The public gate keeps a failing Go test's command and native output."""
    if shutil.which("go") is None:
        pytest.skip("go is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    (repo / "go.mod").write_text("module example.invalid/quality\n\ngo 1.20\n")
    (repo / "answer.go").write_text("package quality\nfunc Answer() int { return 41 }\n")
    (repo / "answer_test.go").write_text(
        'package quality\nimport "testing"\n'
        'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong answer") } }\n'
    )
    subprocess.run(["gofmt", "-w", "answer.go", "answer_test.go"], cwd=repo, check=True)
    head = commit_fixture(repo, "bind failing native Go test")

    completed = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(completed.stdout)
    checks = {check["action_id"]: check for check in payload["data"]["checks"]}
    report = json.loads(checks["behavior"]["stdout"])["providers"][0]["report"]

    assert completed.returncode != 0
    assert payload["verdict"] == "block"
    assert report["required_gaps"] == ["quality_behavior_go_tests_failed"]
    failure = report["diagnostics"][0]
    assert failure["code"] == "go_tests_failed"
    assert failure["observation"]["exit_code"] != 0
    assert "wrong answer" in failure["observation"]["stdout_tail"]


@pytest.mark.parametrize(
    ("sources", "tool_line", "names"),
    [
        (
            {
                "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
                "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            },
            'go = "1.27.1"',
            ("gofmt", "go"),
        ),
        (
            {"package.json": '{"type":"module"}\n', "answer.js": "export const answer = 42;\n"},
            'node = "26.9.0"',
            ("node",),
        ),
    ],
    ids=("go", "node"),
)
def test_declared_mise_supply_precedes_ambient_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    sources: dict[str, str],
    tool_line: str,
    names: tuple[str, ...],
) -> None:
    """A repository's locked tool selection, not host PATH, owns native checks."""
    config = f"[tools]\n{tool_line}\n"
    repo = committed_source_repo(
        tmp_path,
        {
            **sources,
            "mise.toml": config,
            "mise.lock": "lockfile_version = 2\n",
        },
    )
    binary = tmp_path / "locked-bin"
    binary.mkdir()
    for name in (*names, "cue", "rcodesign"):
        executable = binary / name
        executable.write_text("locked tool\n")
        executable.chmod(0o755)
    selected: list[str] = []
    executed: list[tuple[str, ...]] = []

    def select(_root: Path, arguments: tuple[str, ...], **kwargs: object):
        assert kwargs["offline"] is True
        assert kwargs["files"] == {
            native_mise.MISE_CONFIG: config,
            native_mise.MISE_LOCK: "lockfile_version = 2\n",
        }
        if arguments == ("env", "--json"):
            selected.append("env")
            return subprocess.CompletedProcess(arguments, 0, json.dumps({"PATH": str(binary)}), "")
        if arguments == ("bin-paths",):
            selected.append("bin-paths")
            return subprocess.CompletedProcess(arguments, 0, f"{binary}\n", "")
        selected.append(arguments[1])
        return subprocess.CompletedProcess(arguments, 0, f"{binary / arguments[1]}\n", "")

    def execute(_root: Path, command: tuple[str, ...], **kwargs: object):
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        path = environment["PATH"]
        assert isinstance(path, str)
        assert path.split(os.pathsep)[0] == str(binary)
        assert shutil.which("cue", path=path) == str(binary / "cue")
        assert shutil.which("rcodesign", path=path) == str(binary / "rcodesign")
        executed.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(native_mise, "run_mise", select)
    monkeypatch.setattr(native_quality, "run_command", execute)

    report = native_quality.static_report(repo)

    assert report["verdict"] == "pass", report
    assert selected == ["env", "bin-paths", *names]
    assert [Path(command[0]) for command in executed] == [binary / name for name in names]


def test_declared_mise_without_lock_does_not_use_ambient_go(tmp_path: Path) -> None:
    """A missing repository lock is a supply gap, not host-tool permission."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "mise.toml": '[tools]\ngo = "1.27.1"\n',
        },
    )

    assert native_quality.static_report(repo)["required_gaps"] == [
        "quality_static-analysis_locked_toolchain_missing"
    ]


@pytest.mark.parametrize("language", ["go", "javascript"])
@pytest.mark.parametrize("defect", ["none", "syntax", "unexercised", "same-name"])
@pytest.mark.parametrize("gate_owner", ["profile", "registry"])
def test_native_code_provider_checks_real_sources(
    tmp_path: Path, language: str, gate_owner: str, defect: str
) -> None:
    """Public proof rejects absent native evidence and accepts real covered code."""
    executable = "go" if language == "go" else "node"
    if shutil.which(executable) is None:
        pytest.skip(f"{executable} is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, gate_owner)
    if language == "go":
        _write_go_fixture(repo, defect)
    else:
        _write_javascript_fixture(repo, defect)
    head = commit_fixture(repo, "declare native code quality")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert payload["summary"]["proof_attestation_issued"] is False
    if defect == "none":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert payload["required_gaps"] == []
    else:
        assert result.returncode != 0
        assert payload["verdict"] == "block"
        assert any(
            str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
        )
        if defect in {"unexercised", "same-name"}:
            assert "quality_obligation_unproven:behavior" in payload["required_gaps"]


def test_javascript_test_directory_uses_native_test_identity(tmp_path: Path) -> None:
    """An explicit tracked test under tests need not duplicate a filename suffix."""
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "behavior.js").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        'import {answer} from "../answer.js";\n'
        'test("answer", () => assert.equal(answer(), 42));\n'
    )
    head = commit_fixture(repo, "declare directory-owned native test")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0, payload["required_gaps"]
    assert payload["verdict"] == "pass"


def test_public_proof_rejects_test_forged_v8_coverage(tmp_path: Path) -> None:
    """A passing test cannot fabricate execution of an untouched source module."""
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    (repo / "answer.test.js").write_text(
        'import test from "node:test";\n'
        'import { writeFileSync } from "node:fs";\n'
        'import { join, resolve } from "node:path";\n'
        'import { pathToFileURL } from "node:url";\n'
        'test("forged coverage", () => {\n'
        '  const entry = {url: pathToFileURL(resolve("answer.js")).href, '
        "functions: [{ranges: [{count: 1}]}]};\n"
        "  if (process.env.NODE_V8_COVERAGE) "
        '  writeFileSync(join(process.env.NODE_V8_COVERAGE, "coverage-forged.json"), '
        "JSON.stringify({result: [entry]}));\n"
        "});\n"
    )
    head = commit_fixture(repo, "declare forged coverage test")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert "quality_obligation_unproven:behavior" in payload["required_gaps"]


def test_public_proof_rejects_command_authored_evidence_adapter(tmp_path: Path) -> None:
    """An arbitrary repository command cannot mint a product-quality report."""
    repo = init_git_repo(tmp_path / "adopter")
    _declare_quality_profile(repo, "profile")
    profile = repo / ".ethos/profile.toml"
    declaration = profile.read_text(encoding="utf-8").replace(
        'providers = ["ethos.adapters.gates.code_quality:behavior_report"]',
        'command = ["node", "fake.mjs"]\n'
        'evidence_adapters = ["ethos.adapters.gates.native_evidence:javascript_behavior"]',
    )
    profile.write_text(declaration, encoding="utf-8")
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    (repo / "answer.test.js").write_text('throw new Error("never run");\n')
    (repo / "fake.mjs").write_text("process.exit(0);\n")
    head = commit_fixture(repo, "claim command-authored native evidence")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert any("repository_profile_invalid" in str(gap) for gap in payload["required_gaps"])


@pytest.mark.parametrize("defect", ["none", "unexercised", "command-failed"])
def test_public_proof_conjoins_native_commands_with_product_verifiers(
    tmp_path: Path, defect: str
) -> None:
    """Two existing gate IDs retain domain commands and gain real code evidence."""
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    _write_javascript_fixture(repo, defect)
    behavior_command = (
        ["node", "-e", "process.exit(3)"]
        if defect == "command-failed"
        else [
            "node",
            "--test",
            "--experimental-test-coverage",
            "--test-reporter=junit",
            "--test-reporter-destination=stdout",
            "--test-reporter=lcov",
            "--test-reporter-destination=stderr",
            "answer.test.js",
        ]
    )
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "composite-quality-adopter"\n\n'
        '[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
        '[proof.code_correctness_map]\nbehavior = "behavior"\n'
        'static-analysis = "static"\n\n'
        '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
        f"command = {json.dumps(behavior_command)}\n"
        'verification_providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n\n'
        '[[proof.gates]]\nid = "static"\nkind = "lint"\n'
        'command = ["node", "-e", "console.log(\\"format check\\")"]\n'
        'verification_providers = ["ethos.adapters.gates.code_quality:static_report"]\n',
        encoding="utf-8",
    )
    head = commit_fixture(repo, "bind native commands and product verification")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    if defect == "none":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert all(
            check["verification"]["providers"][0]["report"]["verdict"] == "pass"
            for check in payload["data"]["checks"]
        )
    else:
        assert result.returncode != 0
        assert payload["verdict"] == "block"
        assert "quality_obligation_unproven:behavior" in payload["required_gaps"]
    assert [check["action_id"] for check in payload["data"]["checks"]] == ["behavior", "static"]


@pytest.mark.parametrize("exercise_tool", ["exercised", "unexercised"])
@pytest.mark.parametrize("test_root", ["tests", "checks"])
def test_public_python_quality_covers_repository_tool_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exercise_tool: str, test_root: str
) -> None:
    """One native run must cover tools as code, not reject or relabel them as tests."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
    _declare_quality_profile(repo, "profile")
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    (repo / "pyproject.toml").write_bytes((fixture / "pyproject.toml").read_bytes())
    (repo / "uv.lock").write_bytes((fixture / "uv.lock").read_bytes())
    source = repo / "src/sample/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n", encoding="utf-8")
    tool = repo / "tools/utility.py"
    tool.parent.mkdir()
    tool.write_text("def double(value: int) -> int:\n    return value * 2\n", encoding="utf-8")
    test = repo / test_root / "test_sample.py"
    test.parent.mkdir()
    tool_call = (
        "    from tools.utility import double\n    assert double(21) == 42\n"
        if exercise_tool == "exercised"
        else ""
    )
    test.write_text(
        "import os\nfrom pathlib import Path\n\nfrom sample import answer\n\n\n"
        "def test_answer() -> None:\n"
        '    marker = Path(os.environ["ETHOS_TEST_MARKER"])\n'
        '    marker.write_text(marker.read_text() + "x" if marker.exists() else "x")\n'
        "    assert answer() == 42\n" + tool_call,
        encoding="utf-8",
    )
    marker = tmp_path / "run-count"
    monkeypatch.setenv("ETHOS_TEST_MARKER", str(marker))
    adopter_environment = repo / ".venv"
    adopter_environment.mkdir()
    sentinel = adopter_environment / "adopter-owned"
    sentinel.write_bytes(b"retain exactly")
    head = commit_fixture(repo, "bind product and repository-tool quality")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)
    checks = {check["action_id"]: check for check in payload["data"]["checks"]}

    if exercise_tool == "exercised":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        report = json.loads(checks["behavior"]["stdout"])["providers"][0]["report"]
        assert report["quality_evidence"]["selected_paths"] == [
            "src/sample/__init__.py",
            "tools/utility.py",
        ]
    else:
        assert result.returncode != 0
        assert "quality_obligation_unproven:behavior" in payload["required_gaps"]
        assert checks["static"]["verdict"] == "pass"
    assert marker.read_text(encoding="utf-8") == "x"
    assert sentinel.read_bytes() == b"retain exactly"
    assert tuple(adopter_environment.iterdir()) == (sentinel,)
