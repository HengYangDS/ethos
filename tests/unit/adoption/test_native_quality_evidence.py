"""Reject malformed, missing, or misattributed native quality evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.code_quality as native_quality
from ethos.repository.policy.quality_reports import go_covered_paths
from ethos.repository.policy.quality_reports import v8_covered_paths
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("profile", "reason"),
    [
        ([], "go_coverage_invalid"),
        (["not-a-mode"], "go_coverage_invalid"),
        (["mode: set", "invalid row"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 1 nope"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 nope 1"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 1 -1"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 1 0"], "go_source_unexercised"),
        (
            [
                "mode: set",
                "module/answer.go:1.1,1.2 1 0",
                "module/sub/answer.go:1.1,1.2 1 1",
            ],
            "go_source_unexercised",
        ),
    ],
)
def test_go_coverage_rejects_invalid_or_misattributed_blocks(
    profile: list[str], reason: str
) -> None:
    """Go coverage cannot credit a sibling or a malformed profile."""
    with pytest.raises(ValueError, match=reason):
        go_covered_paths(profile, ("answer.go", "sub/answer.go"))


def test_go_coverage_accepts_exact_positive_blocks() -> None:
    """The same parser has a reachable valid path for distinct source names."""
    profile = [
        "mode: set",
        "module/answer.go:1.1,1.2 1 1",
        "module/sub/answer.go:1.1,1.2 1 1",
    ]
    assert go_covered_paths(profile, ("answer.go", "sub/answer.go")) == [
        "answer.go",
        "sub/answer.go",
    ]


@pytest.mark.parametrize(
    "evidence",
    [
        "missing",
        "malformed-json",
        "bad-root",
        "bad-functions",
        "bad-ranges",
        "non-dict-entry",
        "zero-hit",
        "other-file",
    ],
)
def test_javascript_coverage_rejects_unproved_module(tmp_path: Path, evidence: str) -> None:
    """Only positive V8 ranges for the selected file qualify it."""
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "answer.js"
    source.write_text("export const answer = 42;\n")
    coverage = tmp_path / "coverage"
    coverage.mkdir()
    if evidence != "missing":
        if evidence == "malformed-json":
            (coverage / "coverage-1.json").write_text("{invalid")
        else:
            entry = {
                "url": (root / "other.js").as_uri()
                if evidence == "other-file"
                else source.as_uri(),
                "functions": "invalid"
                if evidence == "bad-functions"
                else [{"ranges": "invalid" if evidence == "bad-ranges" else [{"count": 0}]}],
            }
            document = (
                {"result": {"not": "a list"}}
                if evidence == "bad-root"
                else {"result": [42 if evidence == "non-dict-entry" else entry]}
            )
            (coverage / "coverage-1.json").write_text(json.dumps(document))
    reason = (
        "javascript_coverage_missing"
        if evidence == "missing"
        else "javascript_coverage_invalid"
        if evidence
        in {"malformed-json", "bad-root", "bad-functions", "bad-ranges", "non-dict-entry"}
        else "javascript_source_unexercised"
    )
    with pytest.raises(ValueError, match=reason):
        v8_covered_paths(root, coverage, ("answer.js",))


def test_javascript_coverage_accepts_exact_executed_module(tmp_path: Path) -> None:
    """Valid V8 execution metadata is not blocked by the adverse cases."""
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "answer.js"
    source.write_text("export const answer = 42;\n")
    coverage = tmp_path / "coverage"
    coverage.mkdir()
    (coverage / "coverage-1.json").write_text(
        json.dumps(
            {"result": [{"url": source.as_uri(), "functions": [{"ranges": [{"count": 1}]}]}]}
        )
    )
    assert v8_covered_paths(root, coverage, ("answer.js",)) == {"answer.js"}


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


def _committed_source_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    for path, content in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    commit_fixture(repo, "record native source")
    return repo


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
    repo = _committed_source_repo(tmp_path, files)
    report = (
        native_quality.behavior_report(repo)
        if axis == "behavior"
        else native_quality.static_report(repo)
    )
    assert report["required_gaps"] == [f"quality_{axis}_{reason}"]


def test_native_tool_absence_does_not_become_quality_success(tmp_path: Path, monkeypatch) -> None:
    """Unavailable locked native execution is an adverse observation."""
    repo = _committed_source_repo(
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


def test_go_skipped_tests_do_not_prove_behavior(tmp_path: Path) -> None:
    """A package pass with no executed test case is not behavioral proof."""
    repo = _committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.26\n",
            "answer.go": "package quality\n\nfunc Answer() int { return 42 }\n",
            "answer_test.go": 'package quality\n\nimport "testing"\n\n'
            'func TestAnswer(t *testing.T) { t.Skip("not executed") }\n',
        },
    )
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_go_tests_unexecuted"
    ]


def test_go_vet_diagnostics_are_not_silenced(tmp_path: Path) -> None:
    """A parseable but statically invalid Go call remains a failing check."""
    repo = _committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.26\n",
            "answer.go": 'package quality\n\nimport "fmt"\n\n'
            'func Answer() { fmt.Printf("%d", "wrong") }\n',
        },
    )
    assert native_quality.static_report(repo)["required_gaps"] == [
        "quality_static-analysis_go_vet_diagnostics"
    ]


def test_javascript_skipped_tests_do_not_prove_behavior(tmp_path: Path) -> None:
    """A JUnit report with no executed case cannot qualify the source."""
    repo = _committed_source_repo(
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


def test_generic_provider_uses_real_locked_python_evidence(tmp_path: Path) -> None:
    """The generalized provider preserves Python's existing native success path."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "quality-sample"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\n\n'
        '[dependency-groups]\ndev = ["pytest>=9.1.1", "pytest-cov>=7.1.0"]\n\n'
        '[build-system]\nrequires = ["hatchling>=1.32.3"]\n'
        'build-backend = "hatchling.build"\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["src/sample"]\n'
    )
    source = repo / "src/sample/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n")
    test = repo / "tests/test_sample.py"
    test.parent.mkdir()
    test.write_text(
        "from sample import answer\n\n\ndef test_answer() -> None:\n    assert answer() == 42\n"
    )
    locked = subprocess.run(
        (sys.executable, "-m", "uv", "lock", "--offline"),
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert locked.returncode == 0, locked.stderr
    commit_fixture(repo, "lock native Python quality")

    for report in (native_quality.behavior_report(repo), native_quality.static_report(repo)):
        assert report["verdict"] == "pass", report["required_gaps"]
