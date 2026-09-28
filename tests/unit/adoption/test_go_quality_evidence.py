"""Prove native Go quality against exact package, coverage, and source identities."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.code_quality as native_quality
from ethos.repository.policy.quality_reports import go_covered_paths
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from collections.abc import Mapping


@pytest.mark.parametrize(
    ("profile", "reason"),
    [
        ([], "go_coverage_invalid"),
        (["not-a-mode"], "go_coverage_invalid"),
        (["mode: invented"], "go_coverage_invalid"),
        (["mode: set", "invalid row"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 1 nope"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 nope 1"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 1 -1"], "go_coverage_invalid"),
        (["mode: set", "module/answer.go:1.1,1.2 -1 1"], "go_coverage_invalid"),
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
        go_covered_paths(
            profile,
            ("answer.go", "sub/answer.go"),
            {"module/answer.go": "answer.go", "module/sub/answer.go": "sub/answer.go"},
        )


def test_go_coverage_accepts_exact_positive_blocks() -> None:
    """The same parser has a reachable valid path for distinct source names."""
    profile = [
        "mode: set",
        "module/answer.go:1.1,1.2 1 1",
        "module/sub/answer.go:1.1,1.2 1 1",
    ]
    assert go_covered_paths(
        profile,
        ("answer.go", "sub/answer.go"),
        {"module/answer.go": "answer.go", "module/sub/answer.go": "sub/answer.go"},
    ) == [
        "answer.go",
        "sub/answer.go",
    ]


def test_go_coverage_rejects_suffix_alias_from_another_package() -> None:
    """A matching basename is not proof of a Go package-file identity."""
    with pytest.raises(ValueError, match="go_coverage_source_unmapped"):
        go_covered_paths(
            ["mode: set", "other.module/answer.go:1.1,1.2 1 1"],
            ("answer.go",),
            {"module/answer.go": "answer.go"},
        )


def test_go_coverage_rejects_missing_selected_source() -> None:
    """A covered sibling cannot hide an omitted native-selected source."""
    with pytest.raises(ValueError, match="go_coverage_source_missing"):
        go_covered_paths(
            ["mode: set", "module/live.go:1.1,1.2 1 1"],
            ("live.go", "missing.go"),
            {"module/live.go": "live.go", "module/missing.go": "missing.go"},
        )


@pytest.mark.parametrize("sources", [{}, {"module/alien.go": "alien.go"}])
def test_go_coverage_rejects_invalid_source_map(sources: dict[str, str]) -> None:
    """Only native-selected tracked files can define profile identities."""
    with pytest.raises(ValueError, match="go_coverage_source_map_invalid"):
        go_covered_paths(["mode: set"], ("answer.go",), sources)


def test_go_coverage_accepts_independently_proved_statementless_source() -> None:
    """Native zero-block classification, not omission, excuses one source."""
    assert go_covered_paths(
        ["mode: set", "module/live.go:1.1,1.2 1 1"],
        ("live.go", "empty.go"),
        {"module/live.go": "live.go", "module/empty.go": "empty.go"},
        zero_statement_paths=frozenset({"empty.go"}),
    ) == ["live.go"]


@pytest.mark.parametrize("zero_count", [0, 1])
def test_go_zero_statement_source_is_observed_but_not_credited(zero_count: int) -> None:
    """A native zero-statement segment is legal but cannot prove execution."""
    profile = [
        "mode: atomic",
        "module/live.go:1.1,2.1 1 1",
        f"module/empty.go:1.1,2.1 0 {zero_count}",
    ]

    assert go_covered_paths(
        profile,
        ("live.go", "empty.go"),
        {"module/live.go": "live.go", "module/empty.go": "empty.go"},
    ) == ["live.go"]


def test_go_all_zero_statement_profile_cannot_prove_behavior() -> None:
    """An entirely non-applicable native profile is not a coverage success."""
    with pytest.raises(ValueError, match="go_coverage_no_applicable_statements"):
        go_covered_paths(
            ["mode: atomic", "module/empty.go:1.1,2.1 0 0"],
            ("empty.go",),
            {"module/empty.go": "empty.go"},
        )


def test_go_skipped_tests_do_not_prove_behavior(tmp_path: Path) -> None:
    """A package pass with no executed test case is not behavioral proof."""
    repo = committed_source_repo(
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


def test_go_behavior_uses_native_build_scope_and_cross_package_coverage(tmp_path: Path) -> None:
    """Only Go-selected statements require hits, including calls into untested packages."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": 'package quality\nimport "example.invalid/quality/lib"\n'
            "func Answer() int { return lib.Answer() }\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
            "lib/lib.go": "package lib\nfunc Answer() int { return 42 }\n",
            "empty.go": "package quality\ntype Empty struct{}\n",
            "platform_windows.go": "package quality\ntype WindowsOnly struct{}\n",
            "provenance/_source/snapshot.go": (
                "package snapshot\nfunc Historical() int { return 1 }\n"
            ),
        },
    )

    report = native_quality.behavior_report(repo)

    assert report["verdict"] == "pass", report
    native = report["native"]
    assert isinstance(native, list)
    go_report = native[0]
    assert isinstance(go_report, dict)
    covered = go_report["covered_paths"]
    non_applicable = go_report["non_applicable_paths"]
    assert isinstance(covered, list)
    assert isinstance(non_applicable, list)
    assert set(covered) == {"answer.go", "lib/lib.go"}
    assert set(non_applicable) == {
        "empty.go",
        "platform_windows.go",
        "provenance/_source/snapshot.go",
    }


def test_go_behavior_rejects_uncovered_cross_package_statements(tmp_path: Path) -> None:
    """Native package selection cannot make an untested dependency disappear."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
            "lib/unused.go": "package lib\nfunc Unused() int { return 1 }\n",
        },
    )

    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_go_source_unexercised"
    ]


def test_go_behavior_rejects_unlisted_nested_module(tmp_path: Path) -> None:
    """A second module is not silently excused by the root module's wildcard."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
            "addon/go.mod": "module example.invalid/addon\n\ngo 1.20\n",
            "addon/addon.go": "package addon\nfunc Value() int { return 1 }\n",
        },
    )

    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_go_source_scope_unknown"
    ]


def test_go_behavior_rejects_omitted_executable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Go's instrumenter, not a missing profile row, proves applicability."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "missing.go": "package quality\nfunc Missing() int { return 1 }\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
        },
    )
    real_command = native_quality.run_command

    def observed_command(
        root: Path,
        command: tuple[str, ...],
        *,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,
        **_kwargs: object,
    ):
        if command[1] != "test":
            return real_command(root, command, timeout=timeout, env=env)
        option = next(arg for arg in command if arg.startswith("-coverprofile="))
        Path(option.partition("=")[2]).write_text(
            "mode: set\nexample.invalid/quality/answer.go:1.1,1.2 1 1\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            command, 0, '{"Action":"pass","Test":"TestAnswer"}\n', ""
        )

    monkeypatch.setattr(native_quality, "run_command", observed_command)
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_go_coverage_source_missing"
    ]


@pytest.mark.parametrize("outcome", ["failed", "missing-marker", "missing-count"])
def test_go_behavior_rejects_unproved_statementless_classification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    """An omitted build file needs a valid independent Go instrumenter result."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "empty.go": "package quality\ntype Empty struct{}\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
        },
    )
    monkeypatch.setattr(
        native_quality,
        "_go_package_sources",
        lambda _root, _production: {
            "example.invalid/quality/answer.go": "answer.go",
            "example.invalid/quality/empty.go": "empty.go",
        },
    )

    def observed_command(root: Path, command: tuple[str, ...], **_kwargs: object):
        assert root == repo
        output = Path(command[command.index("-o") + 1]) if "-o" in command else None
        if output is not None:
            if outcome == "missing-marker":
                output.write_text("package quality\n")
            elif outcome == "missing-count":
                output.write_text("var EthosCoverageProbe = struct {\nOther [0]uint32\n}\n")
            return subprocess.CompletedProcess(command, int(outcome == "failed"), "", "")
        option = next(arg for arg in command if arg.startswith("-coverprofile="))
        Path(option.partition("=")[2]).write_text(
            "mode: set\nexample.invalid/quality/answer.go:1.1,1.2 1 1\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(
            command, 0, '{"Action":"pass","Test":"TestAnswer"}\n', ""
        )

    monkeypatch.setattr(native_quality, "run_command", observed_command)
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_go_coverage_applicability_unknown"
    ]


@pytest.mark.parametrize(
    ("discovery", "change", "reason"),
    [
        ("failed", {}, "go_package_scope_unavailable"),
        ("invalid-json", {}, "go_package_scope_invalid"),
        ("invalid-object", {}, "go_package_scope_invalid"),
        ("outside-root", {}, "go_package_scope_invalid"),
        ("untracked", {"GoFiles": ["missing.go"]}, "go_package_source_untracked"),
        ("incomplete", {"Incomplete": True}, "go_package_scope_invalid"),
        ("invalid-files", {"GoFiles": "answer.go"}, "go_package_scope_invalid"),
        ("test-source", {"GoFiles": ["answer_test.go"]}, "go_package_scope_invalid"),
        ("missing-identity", {"ImportPath": ""}, "go_package_scope_invalid"),
        ("no-source", {"GoFiles": []}, "go_behavior_source_missing"),
    ],
)
def test_go_behavior_rejects_invalid_native_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    discovery: str,
    change: dict[str, object],
    reason: str,
) -> None:
    """Native package discovery must be complete and bound to tracked source."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            "func TestAnswer(t *testing.T) {}\n",
        },
    )
    package: dict[str, object] = {
        "Dir": str(repo if discovery != "outside-root" else tmp_path),
        "ImportPath": "example.invalid/quality",
        "GoFiles": ["answer.go"],
    }
    package.update(change)
    output = {
        "invalid-json": "not-json",
        "invalid-object": "[]",
    }.get(discovery, json.dumps(package))
    monkeypatch.setattr(
        native_quality,
        "run_command",
        lambda _root, command, **_kwargs: subprocess.CompletedProcess(
            command, 1 if discovery == "failed" else 0, output, ""
        ),
    )
    assert native_quality.behavior_report(repo)["required_gaps"] == [f"quality_behavior_{reason}"]


def test_go_behavior_rejects_ambiguous_native_source_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two repository files cannot claim the same native package-file identity."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\nfunc Answer() int { return 42 }\n",
            "sub/answer.go": "package sub\nfunc Answer() int { return 1 }\n",
            "answer_test.go": 'package quality\nimport "testing"\n'
            "func TestAnswer(t *testing.T) {}\n",
        },
    )
    output = "\n".join(
        json.dumps(
            {
                "Dir": str(directory),
                "ImportPath": "example.invalid/quality",
                "GoFiles": ["answer.go"],
            }
        )
        for directory in (repo, repo / "sub")
    )
    monkeypatch.setattr(
        native_quality,
        "run_command",
        lambda _root, command, **_kwargs: subprocess.CompletedProcess(command, 0, output, ""),
    )

    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_go_package_scope_invalid"
    ]


@pytest.mark.parametrize(
    ("returncode", "stdout", "coverage_text", "reason"),
    [
        (1, '{"Action":"fail","Test":"TestAnswer"}\n', None, "go_tests_failed"),
        (0, '{"Action":"pass","Test":"TestAnswer"}\n', None, "go_coverage_missing"),
        (
            0,
            "not-json\n",
            "mode: set\nexample.invalid/quality/answer.go:1.1,1.2 1 1\n",
            "go_test_report_invalid",
        ),
    ],
)
def test_go_behavior_rejects_failed_or_incomplete_native_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    coverage_text: str | None,
    reason: str,
) -> None:
    """A successful process alone cannot substitute for tests and coverage evidence."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.26\n",
            "answer.go": "package quality\n\nfunc Answer() int { return 42 }\n",
            "answer_test.go": 'package quality\n\nimport "testing"\n\n'
            'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n',
        },
    )

    def observed_command(root: Path, command: tuple[str, ...], **_kwargs: object):
        assert root == repo
        assert command[1:3] == ("test", "-json")
        if coverage_text is not None:
            option = next(arg for arg in command if arg.startswith("-coverprofile="))
            Path(option.partition("=")[2]).write_text(coverage_text)
        return subprocess.CompletedProcess(command, returncode, stdout, "")

    monkeypatch.setattr(native_quality, "_executable", lambda name: name)
    monkeypatch.setattr(
        native_quality,
        "_go_package_sources",
        lambda _root, _production: {"example.invalid/quality/answer.go": "answer.go"},
    )
    monkeypatch.setattr(native_quality, "run_command", observed_command)
    assert native_quality.behavior_report(repo)["required_gaps"] == [f"quality_behavior_{reason}"]


def test_go_behavior_reports_non_applicable_source_without_crediting_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One real covered source can coexist with an observed zero-statement file."""
    repo = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.26\n",
            "live.go": "package quality\nfunc Live() int { return 1 }\n",
            "empty.go": "package quality\n",
            "live_test.go": "package quality\n",
        },
    )

    def observed_command(root: Path, command: tuple[str, ...], **_kwargs: object):
        assert root == repo
        option = next(arg for arg in command if arg.startswith("-coverprofile="))
        Path(option.partition("=")[2]).write_text(
            "mode: atomic\n"
            "example.invalid/quality/live.go:1.1,2.1 1 1\n"
            "example.invalid/quality/empty.go:1.1,2.1 0 0\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, '{"Action":"pass","Test":"TestLive"}\n', "")

    monkeypatch.setattr(native_quality, "_executable", lambda name: name)
    monkeypatch.setattr(
        native_quality,
        "_go_package_sources",
        lambda _root, _production: {
            "example.invalid/quality/live.go": "live.go",
            "example.invalid/quality/empty.go": "empty.go",
        },
    )
    monkeypatch.setattr(native_quality, "run_command", observed_command)
    report = native_quality.behavior_report(repo)

    assert report["verdict"] == "pass"
    quality_evidence = report["quality_evidence"]
    assert isinstance(quality_evidence, dict)
    assert quality_evidence["selected_paths"] == ["empty.go", "live.go"]
    assert report["native"] == [
        {
            "language": "go",
            "tests_passed": 1,
            "covered_paths": ["live.go"],
            "non_applicable_paths": ["empty.go"],
        }
    ]


def test_go_vet_diagnostics_are_not_silenced(tmp_path: Path) -> None:
    """A parseable but statically invalid Go call remains a failing check."""
    repo = committed_source_repo(
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
