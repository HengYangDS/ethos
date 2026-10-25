"""Reject malformed, missing, or misattributed native quality evidence."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.javascript.analysis as analysis
import ethos.adapters.gates.javascript.behavior as javascript_behavior
import ethos.adapters.toolchain.mise as native_mise
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.store.state.schema import local_state_root
from ethos.repository.policy.code_subjects import observed_code_subjects
from ethos.repository.policy.quality_reports import istanbul_coverage_report
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo
from tests.support.mise_host import outside_ci
from tests.support.proof import declare_quality_profile
from tests.support.proof import run_quality_proof


@pytest.mark.parametrize("role", ["code", "tooling", "snapshot", "config", "generated"])
def test_native_c8_selection_is_not_overridden_and_unselected_authored_source_stays_unproved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """Native includes select coverage, not authority to omit authored obligations."""
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitattributes": f"omitted.js ethos-role={role}\n",
            "package.json": json.dumps(
                {
                    "type": "module",
                    "scripts": {
                        "test": "node --test answer.test.js",
                        "test:coverage": "c8 --config .config/coverage.json npm test",
                    },
                }
            ),
            ".config/coverage.json": json.dumps({"all": True, "include": ["answer.js"]}),
            "answer.js": "export function answer() { return 42; }\n",
            "omitted.js": "export function unproved() { return 0; }\n",
            "answer.test.js": 'import test from "node:test"; import {answer} from "./answer.js";\n'
            'test("answer", () => { if (answer() !== 42) throw Error("wrong"); });\n',
        },
    )
    subjects = observed_code_subjects(
        ("answer.js", "answer.test.js", "omitted.js"), roles={"omitted.js": role}
    )
    node = shutil.which("node")
    assert node is not None
    report = javascript_behavior.behavior_observation(repo, subjects, None, node, {})
    assert isinstance(report["coverage_execution"], dict)
    argv = report["coverage_execution"]["argv"]
    assert not any(value.startswith(("--include=", "--exclude=")) for value in argv)
    assert "--all" not in argv
    assert "--exclude-node-modules=false" not in argv
    assert report["verdict"] == ("block" if role in {"code", "generated"} else "pass")
    assert isinstance(report["native_selection"], dict)
    assert report["native_selection"]["selected_paths"] == ["answer.js"]
    assert report["unselected_paths"] == ["omitted.js"]


def test_generated_role_cannot_replace_authored_coverage(tmp_path: Path) -> None:
    """Executing a role-labelled input does not establish native artifact provenance."""
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitattributes": "generated.js ethos-role=generated\n",
            "package.json": json.dumps(
                {
                    "type": "module",
                    "scripts": {
                        "test": "node --test answer.test.js",
                        "test:coverage": "c8 --include answer.js npm test",
                    },
                }
            ),
            "generated.js": "export const generated = 42;\n",
            "answer.js": 'import {generated} from "./generated.js";\n'
            "export function answer() { return generated; }\n",
            "answer.test.js": 'import test from "node:test"; import {answer} from "./answer.js";\n'
            'test("answer", () => { if (answer() !== 42) throw Error("wrong"); });\n',
        },
    )
    subjects = observed_code_subjects(
        ("answer.js", "answer.test.js", "generated.js"), roles={"generated.js": "generated"}
    )
    node = shutil.which("node")
    assert node is not None
    report = javascript_behavior.behavior_observation(repo, subjects, None, node, {})
    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert "javascript_coverage_subject_unselected:generated.js" in gaps
    assert report["executed_generated_paths"] == []


@pytest.mark.parametrize("defect", ["none", "missing", "alias", "counter", "scope"])
def test_javascript_coverage_conserves_native_subjects(tmp_path: Path, defect: str) -> None:
    """Only complete native counts on exact selected paths qualify the observation."""
    axes = {
        key: {"total": 1, "covered": 1, "skipped": 0}
        for key in ("lines", "branches", "functions", "statements")
    }
    source = str(tmp_path / "answer.js")
    document = {"total": axes, source: axes}
    if defect == "missing":
        document = {}
    elif defect == "alias":
        document[str(tmp_path) + "/./answer.js"] = axes
    elif defect == "counter":
        axes["branches"]["covered"] = 2
    elif defect == "scope":
        document[str(tmp_path / "other.js")] = document.pop(source)
    report = tmp_path / "coverage-summary.json"
    report.write_text(json.dumps(document))
    if defect == "none":
        assert istanbul_coverage_report(tmp_path, report, ("answer.js",))[1] == {"answer.js"}
    else:
        with pytest.raises(ValueError, match="javascript_coverage_"):
            istanbul_coverage_report(tmp_path, report, ("answer.js",))


@pytest.mark.parametrize("launcher", ["node", "npm", "mise"])
def test_verified_node_behavior_rejects_wrong_scope_or_toolchain(
    tmp_path: Path, launcher: str
) -> None:
    """An outer attempt without owned V8 custody remains unproved and is never replayed."""
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.js": "export function answer() { return 42; }\n",
            "answer.test.js": 'import test from "node:test";\n'
            'import {writeFileSync} from "node:fs";\n'
            'test("must not replay", () => writeFileSync("replayed", "bad"));\n',
        },
    )
    execution = NativeExecution(
        (launcher, "test"),
        (launcher, "test"),
        repo.resolve(),
        0,
        "outer native output",
        "retained native diagnostic",
        executable=shutil.which("node") or "",
    )
    report = native_quality.behavior_report(repo, execution=execution)
    assert report["required_gaps"] == [
        "quality_behavior_javascript_native_coverage_custody_unavailable"
    ]
    assert not (repo / "replayed").exists()
    assert isinstance(report["native"], list)
    assert report["native"][0]["stderr"] == "retained native diagnostic"


@pytest.mark.parametrize("outcome", ["pass", "test-failure", "coverage-failure", "warning"])
def test_provider_only_javascript_does_not_credit_a_failed_native_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    """One native test and its same-attempt c8 report preserve independent outcomes."""
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    if shutil.which("node") is None:
        pytest.skip("node is unavailable on this runner")
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitignore": "runs\n",
            "package.json": json.dumps(
                {
                    "name": "quality",
                    "type": "module",
                    "scripts": {
                        "test": "node --import=./preload.mjs --test "
                        "--test-concurrency=2 answer.test.js",
                        "test:coverage": "c8 --config .config/coverage.json npm test",
                    },
                }
            ),
            ".config/coverage.json": json.dumps(
                {"all": True, "lines": 95, "statements": 95, "branches": 95, "functions": 95}
            ),
            "preload.mjs": "globalThis.expectedAnswer = 42;\n",
            "answer.js": "export function answer() { return 42; }\n",
            "answer.test.js": (
                'import test from "node:test";\nimport {appendFileSync} from "node:fs";\n'
                'import {answer} from "./answer.js";\n'
                'test("answer", () => { appendFileSync("runs", "x"); '
                + ('process.emitWarning("native warning");' if outcome == "warning" else "")
                + (
                    'answer(); throw Error("native failure");'
                    if outcome == "test-failure"
                    else "if (answer() !== globalThis.expectedAnswer) "
                    'throw Error("preload missing");'
                )
                + " });\n"
            ),
        },
    )

    if outcome == "coverage-failure":
        (repo / "unused.js").write_text("export const neverUsed = 1;\n")
        commit_fixture(repo, "include uncovered subject")
    declare_quality_profile(repo)
    head = commit_fixture(
        repo,
        "bind one native attempt to public quality",
        format_paths=(
            ".ethos/profile.toml",
            "package.json",
            ".config/coverage.json",
            "preload.mjs",
            "answer.js",
            "answer.test.js",
        ),
    )
    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)
    assert result.returncode == int(outcome != "pass"), payload["required_gaps"]
    assert payload["verdict"] == ("pass" if outcome == "pass" else "block"), payload
    assert (repo / "runs").read_text() == "x"
    (artifact,) = (local_state_root(repo) / "artifacts").glob("*.zip")
    with ZipFile(artifact) as archive:
        observed = json.loads(archive.read("observation.json"))
    assert "--import=./preload.mjs" in observed["test_execution"]["argv"]
    assert "--test-concurrency=2" in observed["test_execution"]["argv"]
    assert not any(
        "experimental-test-coverage" in value for value in observed["test_execution"]["argv"]
    )
    assert observed["test_execution"]["exit_code"] == int(outcome == "test-failure")
    assert observed["coverage_execution"]["exit_code"] == int(outcome == "coverage-failure")
    assert "--config" in observed["coverage_execution"]["argv"]
    assert observed["raw_identity_preserved"]
    assert not Path(observed["raw_directory"]).exists()


def test_native_node_custody_does_not_follow_rejected_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rejected raw links never copy unrelated target bytes into retained evidence."""
    sentinel = tmp_path / "foreign"
    sentinel.write_bytes(b"unrelated bytes must not be read")
    link = tmp_path / "capability"
    try:
        link.symlink_to(sentinel)
    except OSError:
        pytest.skip("native symlink creation is unavailable")
    link.unlink()
    monkeypatch.setenv("ETHOS_CUSTODY_SENTINEL", str(sentinel))
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.js": "export const answer = 42;\n",
            "answer.test.js": 'import test from "node:test";\n'
            'import {symlinkSync} from "node:fs"; import {join} from "node:path";\n'
            'import {answer} from "./answer.js";\n'
            'test("custody", () => { if (answer !== 42) throw Error(); '
            "symlinkSync(process.env.ETHOS_CUSTODY_SENTINEL, "
            'join(process.env.NODE_V8_COVERAGE, "link")); });\n',
        },
    )
    report = native_quality.behavior_report(repo)
    assert report["required_gaps"] == ["quality_behavior_javascript_native_coverage_input_invalid"]
    assert isinstance(report["native"], list)
    with ZipFile(report["native"][0]["artifact"]["path"]) as archive:
        assert "raw/link" not in archive.namelist()
    assert sentinel.read_bytes() == b"unrelated bytes must not be read"


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
    ("source", "verdict"),
    [
        ("printf '%s\\n' 'ready'\n", "pass"),
        ("if true; then\n", "block"),
        ("echo $value\n", "block"),
    ],
)
def test_native_script_static_checks_without_executing_tooling(
    tmp_path: Path, source: str, verdict: str
) -> None:
    """A native script role requires lexical evidence, never running the build tool."""
    repo = committed_source_repo(
        tmp_path,
        {".gitattributes": "build.sh ethos-role=tooling\n", "build.sh": f"#!/bin/sh\n{source}"},
    )
    report = native_quality.static_report(repo)
    assert report["verdict"] == verdict, report
    assert isinstance(report["native"], list)
    assert report["native"][0]["tool"] == "shellcheck"


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
        (
            {"package.json": '{"type":"module"}\n', "answer.test.js": "export {};\n"},
            "behavior",
            "javascript_tests_or_sources_missing",
        ),
        ({"test_answer.py": "def test_answer(): pass\n"}, "behavior", "scope_unrecognized"),
        (
            {
                "answer.js": "export const answer = 42;\n",
                ".gitattributes": "answer.js ethos-role=snapshot\n",
            },
            "behavior",
            "source_contract_missing:answer.js",
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
    assert report["verdict"] == "block", report
    assert "quality_evidence" not in report
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

    def unavailable() -> Path:
        message = "native_tool_unavailable:node"
        raise ValueError(message)

    monkeypatch.setattr(analysis, "resolve_node_runtime", unavailable)
    assert native_quality.static_report(repo)["required_gaps"] == [
        "quality_static-analysis_native_tool_unavailable:node"
    ]


def test_unavailable_locked_node_does_not_fall_back_to_host_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declared locked tool remains required when an ambient binary exists.

    The repository is untrusted, so the refusal names native trust as the next action.
    """
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.js": "export const answer = 42;\n",
            "mise.toml": '[tools]\nnode = "26.9.0"\n',
            "mise.lock": "lockfile_version = 2\n",
        },
    )
    outside_ci(monkeypatch, repo)
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

    refusal = "quality_static-analysis_mise_supply_unavailable:node:locked node unavailable"
    trust = shlex.join(("mise", "--cd", str(repo.resolve()), "trust"))
    assert native_quality.static_report(repo)["required_gaps"] == [f"{refusal}; next: {trust}"]


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
    report = native_quality.behavior_report(repo)
    assert report["verdict"] == "block"
    assert isinstance(report["required_gaps"], list)
    assert "quality_behavior_javascript_tests_failed" in report["required_gaps"]
    assert isinstance(report["native"], list)
    assert report["native"][0]["tests"]["passed"] == 0


@pytest.mark.parametrize(
    "diagnostic",
    ["", "process.emitWarning('reported warning');", "console.warn('reported warning');"],
)
def test_native_node_behavior_retains_same_attempt_diagnostics(
    tmp_path: Path,
    diagnostic: str,
) -> None:
    """Native reports must retain diagnostics without replaying executed tests."""
    repo = init_git_repo(tmp_path / "adopter")
    marker = tmp_path / "run-count"
    (repo / "package.json").write_text('{"type":"module"}\n')
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    (repo / "answer.test.js").write_text(
        'import test from "node:test"; import assert from "node:assert/strict";'
        'import { appendFileSync } from "node:fs"; import { answer } from "./answer.js";'
        f'test("answer", () => {{ appendFileSync({json.dumps(str(marker))}, "run\\n");'
        f"{diagnostic} assert.equal(answer(), 42); }});\n"
    )
    commit_fixture(repo, "native diagnostic source")
    report = native_quality.behavior_report(repo)
    assert report["verdict"] == ("block" if diagnostic else "pass"), report
    assert marker.read_text() == "run\n"
    assert "native" in report
    assert isinstance(report["native"], list)
    native = report["native"][0]
    assert native["stdout"] == ""
    assert native["stderr"] == ""
    assert native["journal"] != native["stdout"]
    if diagnostic:
        assert "reported warning" in native["journal"]
        assert any("reported warning" in message for message in native["diagnostics"])
    else:
        assert not native["diagnostics"]
    with ZipFile(native["artifact"]["path"]) as archive:
        observed = json.loads(archive.read("observation.json"))
        assert observed["stdout"] == native["stdout"]
        assert observed["stderr"] == native["stderr"]
        assert observed["journal"] == native["journal"]
        assert observed["diagnostics"] == list(native["diagnostics"])


def test_native_quality_does_not_attribute_dirty_bytes_to_committed_source(tmp_path: Path) -> None:
    """A clean working replacement cannot certify a different committed implementation."""
    repo = committed_source_repo(
        tmp_path,
        {
            "package.json": '{"type":"module"}\n',
            "answer.js": "export function answer() { return undefined_value; }\n",
        },
    )
    (repo / "answer.js").write_text("export function answer() { return 42; }\n")
    report = native_quality.static_report(repo)
    assert report["verdict"] == "block", report
    assert "quality_evidence" not in report
    assert report["required_gaps"] == ["quality_static-analysis_code_source_changed"]
