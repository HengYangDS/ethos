"""Reject malformed, missing, or misattributed native quality evidence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.python_quality as python_quality
from ethos.repository.policy.quality_reports import lcov_covered_paths
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo


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


def test_generic_provider_uses_real_locked_python_evidence(tmp_path: Path) -> None:
    """The generalized provider preserves Python's existing native success path."""
    repo = init_git_repo(tmp_path / "repo")
    fixture = Path(__file__).resolve().parents[2] / "fixtures/quality-sample"
    for name in ("pyproject.toml", "uv.lock"):
        (repo / name).write_bytes((fixture / name).read_bytes())
    source = repo / "src/sample/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n")
    test = repo / "tests/test_sample.py"
    test.parent.mkdir()
    test.write_text(
        "from sample import answer\n\n\ndef test_answer() -> None:\n    assert answer() == 42\n"
    )
    commit_fixture(repo, "lock native Python quality")

    for report in (native_quality.behavior_report(repo), native_quality.static_report(repo)):
        assert report["verdict"] == "pass", report["required_gaps"]


def test_native_quality_requires_committed_python_scope(tmp_path: Path) -> None:
    """No HEAD or selected Python file must not become an empty success."""
    untracked = tmp_path / "untracked"
    untracked.mkdir()
    assert python_quality.static_report(untracked)["required_gaps"] == [
        "quality_static_source_head_missing"
    ]

    repo = init_git_repo(tmp_path / "repo")
    assert python_quality.static_report(repo)["required_gaps"] == [
        "quality_static_python_sources_missing"
    ]


def test_native_behavior_requires_source_tests_and_a_lock(tmp_path: Path) -> None:
    """An unrecognized or unlocked scope cannot claim behavior coverage."""
    repo = init_git_repo(tmp_path / "repo")
    source = repo / "src/app.py"
    source.parent.mkdir()
    source.write_text("def answer(): return 42\n", encoding="utf-8")
    commit_fixture(repo, "add source without tests")
    assert python_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_scope_unrecognized"
    ]

    test = repo / "tests/test_app.py"
    test.parent.mkdir()
    test.write_text("def test_answer(): assert True\n", encoding="utf-8")
    commit_fixture(repo, "add tests without lock")
    assert python_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_locked_toolchain_missing"
    ]


@pytest.mark.parametrize(
    ("stdout", "returncode", "gap"),
    [
        ("{", 0, "quality_static_report_invalid"),
        ("{}", 0, "quality_static_report_invalid"),
        ("[]", 1, "quality_static_diagnostics"),
        ('[{"code":"E999"}]', 1, "quality_static_diagnostics"),
    ],
)
def test_native_static_adapter_distinguishes_report_from_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    returncode: int,
    gap: str,
) -> None:
    """A malformed tool report differs from a valid report containing findings."""
    monkeypatch.setattr(python_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=stdout, returncode=returncode),
    )
    assert python_quality.static_report(tmp_path)["required_gaps"] == [gap]


@pytest.mark.parametrize("toolchain", ["product", "mise"])
def test_python_behavior_preserves_selected_locked_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, toolchain: str
) -> None:
    """Native mise never syncs; product uv uses an isolated environment."""
    native_mise = toolchain == "mise"
    if native_mise:
        (tmp_path / "mise.toml").write_text('[tools]\nuv = "0.12.18"\n', encoding="utf-8")
        (tmp_path / "mise.lock").write_text("[tools]\n", encoding="utf-8")

    def observe(_root: Path, command: tuple[str, ...], **options: object) -> None:
        removed = options["remove_env"]
        assert isinstance(removed, tuple)
        assert "UV_PROJECT_ENVIRONMENT" in removed
        environment = options["env"]
        assert isinstance(environment, dict)
        if native_mise:
            assert command[:4] == ("/native/mise", "exec", "--locked", "--")
            assert "--no-sync" in command
            assert environment["MISE_AUTO_INSTALL"] == "0"
            assert environment["MISE_OFFLINE"] == "1"
        else:
            selected = environment["UV_PROJECT_ENVIRONMENT"]
            assert isinstance(selected, str)
            assert not Path(selected).is_relative_to(tmp_path)
        message = "observed"
        raise ValueError(message)

    monkeypatch.setattr(
        python_quality, "mise_executable", lambda: Path("/native/mise"), raising=False
    )
    monkeypatch.setattr(python_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        python_quality,
        "_behavior_scope",
        lambda _root, _paths: (("src/app.py",), ("tests/test_app.py",)),
    )
    monkeypatch.setattr(python_quality, "run_command", observe)
    assert python_quality.behavior_report(tmp_path)["required_gaps"] == [
        "quality_behavior_observed"
    ]


@pytest.mark.parametrize(
    ("exit_code", "reason"), [(0, "test_report_missing"), (1, "test_command_failed")]
)
def test_python_behavior_distinguishes_command_failure_from_missing_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int, reason: str
) -> None:
    """A failed locked tool must not masquerade as a filesystem-only failure."""
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=exit_code, stdout="", stderr=""),
    )
    monkeypatch.setattr(python_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        python_quality,
        "_behavior_scope",
        lambda _root, _paths: (("src/app.py",), ("tests/test_app.py",)),
    )
    assert python_quality.behavior_report(tmp_path)["required_gaps"] == [
        f"quality_behavior_{reason}"
    ]
