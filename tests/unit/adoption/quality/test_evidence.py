"""Reject malformed, missing, or misattributed native quality evidence."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.toolchain.mise as native_mise
from ethos.adapters.gates.verification import NativeExecution
from ethos.repository.policy.quality_reports import lcov_covered_paths
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("evidence", "reason"),
    [
        (None, "javascript_coverage_missing"),
        ("not-lcov", "javascript_coverage_invalid"),
        ("SF:answer.js\nDA:1,1\n", "javascript_coverage_invalid"),
        ("SF:\nDA:1,1\nend_of_record\n", "javascript_coverage_invalid"),
        ("SF:answer.js\nDA:1,-1\nend_of_record\n", "javascript_coverage_invalid"),
        ("SF:answer.js\nDA:1,0\nend_of_record\n", "javascript_source_unexercised"),
        ("SF:other.js\nDA:1,1\nend_of_record\n", "javascript_source_unexercised"),
        ("SF:sub/answer.js\nDA:1,1\nend_of_record\n", "javascript_source_unexercised"),
    ],
)
def test_javascript_coverage_rejects_unproved_module(
    tmp_path: Path, evidence: str | None, reason: str
) -> None:
    """Only positive LCOV line counters for the selected file qualify it."""
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "answer.js"
    source.write_text("export const answer = 42;\n")
    coverage = tmp_path / "coverage.lcov"
    if evidence is not None:
        coverage.write_text(evidence)
    with pytest.raises(ValueError, match=reason):
        lcov_covered_paths(root, coverage, ("answer.js",))


def test_javascript_coverage_accepts_exact_executed_module(tmp_path: Path) -> None:
    """A native LCOV record with a positive line hit has a reachable success path."""
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "answer.js"
    source.write_text("export const answer = 42;\n")
    coverage = tmp_path / "coverage.lcov"
    coverage.write_text("TN:\nSF:answer.js\nDA:1,1\nend_of_record\n")
    assert lcov_covered_paths(root, coverage, ("answer.js",)) == {"answer.js"}


@pytest.mark.parametrize("scenario", ["honest", "forged", "docs-only"])
def test_public_verified_node_behavior_consumes_its_own_reports_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    """A native test runs once, and test-authored output cannot forge coverage."""
    forged_coverage = scenario == "forged"
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    marker = tmp_path / "runs"
    monkeypatch.setenv("ETHOS_TEST_RUN_MARKER", str(marker))
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    behavior_command = (
        ["node", "-e", 'console.log("docs checked")']
        if scenario == "docs-only"
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
    profile.write_text(
        'profile_id = "native-reuse-adopter"\n\n'
        '[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
        '[proof.code_correctness_map]\nbehavior = "behavior"\n'
        'static-analysis = "static"\n\n'
        '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
        f"command = {json.dumps(behavior_command)}\n"
        'verification_providers = ["ethos.adapters.gates.code_quality:behavior_report"]\n\n'
        '[[proof.gates]]\nid = "static"\nkind = "lint"\n'
        'providers = ["ethos.adapters.gates.code_quality:static_report"]\n',
        encoding="utf-8",
    )
    (repo / "package.json").write_text('{"name":"quality","type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    imported = 'import { answer } from "./answer.js";\n' if not forged_coverage else ""
    behavior = (
        'process.stderr.write("TN:\\nSF:answer.js\\nDA:1,1\\nend_of_record\\n");'
        if forged_coverage
        else "assert.equal(answer(), 42);"
    )
    (repo / "answer.test.js").write_text(
        'import test from "node:test";\n'
        'import assert from "node:assert/strict";\n'
        'import { appendFileSync } from "node:fs";\n'
        + imported
        + 'test("answer", () => {\n'
        + '  appendFileSync(process.env.ETHOS_TEST_RUN_MARKER, "x");\n'
        + f"  {behavior}\n"
        + "});\n"
    )
    head = commit_fixture(repo, "bind native Node test reports")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert (result.returncode == 0) is not forged_coverage, payload["required_gaps"]
    assert payload["verdict"] == ("block" if forged_coverage else "pass")
    assert marker.read_text() == "x"


@pytest.mark.parametrize(
    ("scenario", "gap"),
    [
        ("wrong-test", "javascript_native_test_selection_invalid"),
        ("ambient-tool", "javascript_native_toolchain_unbound"),
        ("all-skipped", "javascript_tests_failed"),
        ("invalid-junit", "junit_invalid"),
    ],
)
def test_verified_node_behavior_rejects_wrong_scope_or_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str, gap: str
) -> None:
    """A valid-looking report cannot replace test selection or locked supply."""
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"name":"quality","type":"module"}\n',
            "answer.js": "export function answer() { return 42; }\n",
            "answer.test.js": 'import test from "node:test";\n',
        },
    )
    if scenario == "ambient-tool":
        monkeypatch.setattr(
            native_quality, "_native_environment", lambda _root, _scope: {"PATH": "locked"}
        )
        actual_which = native_quality.shutil.which

        def selected_tool(name: str, path: str | None = None) -> str | None:
            if name == "node":
                return str(tmp_path / ("locked-node" if path else "ambient-node"))
            return actual_which(name, path=path)

        monkeypatch.setattr(native_quality.shutil, "which", selected_tool)
    stdout = {
        "all-skipped": '<testsuites><testcase name="answer"><skipped /></testcase></testsuites>',
        "invalid-junit": "not-junit",
    }.get(scenario, '<testsuites><testcase name="answer" /></testsuites>')
    execution = NativeExecution(
        declared_identity=("node", "--test"),
        argv=(
            "node",
            "--test",
            "--experimental-test-coverage",
            "--test-reporter=junit",
            "--test-reporter-destination=stdout",
            "--test-reporter=lcov",
            "--test-reporter-destination=stderr",
            "other.test.js" if scenario == "wrong-test" else "answer.test.js",
        ),
        cwd=repo.resolve(),
        exit_code=0,
        stdout=stdout,
        stderr="TN:\nSF:answer.js\nDA:1,1\nend_of_record\n",
    )

    assert native_quality.behavior_report(repo, execution=execution)["required_gaps"] == [
        f"quality_behavior_{gap}"
    ]


def test_provider_only_javascript_does_not_credit_a_failed_native_test(tmp_path: Path) -> None:
    """A product-owned test run must retain its own nonzero native result."""
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"name":"quality","type":"module"}\n',
            "answer.js": "export function answer() { return 42; }\n",
            "answer.test.js": (
                'import test from "node:test";\ntest("failure", () => { throw Error(); });\n'
            ),
        },
    )

    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_javascript_tests_failed"
    ]


def test_native_provider_rejects_missing_repository_and_code(tmp_path: Path) -> None:
    """Neither absent Git identity nor a code-free tree can satisfy a code gate."""
    empty = tmp_path / "empty"
    empty.mkdir()
    assert native_quality.behavior_report(empty)["required_gaps"] == [
        "quality_behavior_source_head_missing"
    ]
    repo = init_git_repo(tmp_path / "repo")
    (repo / "README.md").write_text("# Sample\n")
    commit_fixture(repo, "record a document")
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_code_sources_missing"
    ]


def test_native_provider_rejects_deleted_committed_source(tmp_path: Path) -> None:
    """An exact tree identity cannot license missing working source bytes."""
    repo = init_git_repo(tmp_path / "repo")
    source = repo / "answer.js"
    source.write_text("export const answer = 42;\n")
    commit_fixture(repo, "record source")
    source.unlink()
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_code_source_unavailable"
    ]


@pytest.mark.parametrize(
    ("path", "reason"),
    [("answer.go", "go_tests_or_module_missing"), ("answer.js", "javascript_package_missing")],
)
def test_native_provider_requires_native_project_context(
    tmp_path: Path, path: str, reason: str
) -> None:
    """A source suffix alone never qualifies native execution context."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / path).write_text("source\n")
    commit_fixture(repo, "record unbound source")
    assert native_quality.behavior_report(repo)["required_gaps"] == [f"quality_behavior_{reason}"]


@pytest.mark.parametrize(
    ("files", "axis", "reason"),
    [
        (
            {
                "go.mod": "module example.invalid/quality\n\ngo 1.26\n",
                "only_test.go": "package quality\n",
            },
            "behavior",
            "go_behavior_source_missing",
        ),
        ({"answer.go": "package quality\n"}, "static-analysis", "go_module_missing"),
        (
            {"answer.js": "export const answer = 42;\n"},
            "static-analysis",
            "javascript_package_missing",
        ),
        (
            {"package.json": '{"type":"module"}\n', "answer.js": "export const answer = 42;\n"},
            "behavior",
            "javascript_tests_or_sources_missing",
        ),
    ],
)
def test_native_provider_requires_executable_scope(
    tmp_path: Path, files: dict[str, str], axis: str, reason: str
) -> None:
    """A manifest, production source, and tests have distinct obligations."""
    repo = committed_source_repo(tmp_path, files)
    report = (
        native_quality.behavior_report(repo)
        if axis == "behavior"
        else native_quality.static_report(repo)
    )
    assert report["required_gaps"] == [f"quality_{axis}_{reason}"]


def test_native_tool_absence_does_not_become_quality_success(tmp_path: Path, monkeypatch) -> None:
    """Unavailable locked native execution is an adverse observation."""
    repo = committed_source_repo(
        tmp_path,
        {"package.json": '{"type":"module"}\n', "answer.js": "export const answer = 42;\n"},
    )
    original_which = native_quality.shutil.which
    monkeypatch.setattr(
        native_quality.shutil,
        "which",
        lambda name, *args, **kwargs: (
            None if name == "node" else original_which(name, *args, **kwargs)
        ),
    )
    assert native_quality.static_report(repo)["required_gaps"] == [
        "quality_static-analysis_native_tool_unavailable:node"
    ]


def test_unavailable_locked_node_does_not_fall_back_to_host_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declared locked tool remains required when an ambient binary exists."""
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.js": "export const answer = 42;\n",
            "mise.toml": '[tools]\nnode = "26.9.0"\n',
            "mise.lock": "lockfile_version = 2\n",
        },
    )
    original_which = native_quality.shutil.which
    monkeypatch.setattr(
        native_quality.shutil,
        "which",
        lambda name, *args, **kwargs: (
            "/ambient/node" if name == "node" else original_which(name, *args, **kwargs)
        ),
    )
    monkeypatch.setattr(
        native_mise,
        "run_mise",
        lambda _root, arguments, **_kwargs: subprocess.CompletedProcess(
            arguments,
            0 if arguments in {("env", "--json"), ("bin-paths",)} else 1,
            '{"PATH":"/ambient/node"}'
            if arguments == ("env", "--json")
            else f"{tmp_path}\n"
            if arguments == ("bin-paths",)
            else "",
            "" if arguments in {("env", "--json"), ("bin-paths",)} else "locked node unavailable",
        ),
    )

    assert native_quality.static_report(repo)["required_gaps"] == [
        "quality_static-analysis_mise_supply_unavailable:node:locked node unavailable"
    ]


def test_javascript_skipped_tests_do_not_prove_behavior(tmp_path: Path) -> None:
    """A JUnit report with no executed case cannot qualify the source."""
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.js": "export const answer = 42;\n",
            "answer.test.js": 'import test from "node:test";\n'
            'test.skip("not executed", () => {});\n',
        },
    )
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_javascript_tests_failed"
    ]
