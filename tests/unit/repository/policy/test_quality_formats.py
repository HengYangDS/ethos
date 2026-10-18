"""Read tool-neutral coverage and static reports without granting proof authority."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.quality.formats import lcov_files
from ethos.repository.policy.quality.formats import sarif_report
from ethos.repository.policy.quality_reports import coverage_stream_report

if TYPE_CHECKING:
    from pathlib import Path

_TRACKED = frozenset({"bin/run.sh", "lib/util.sh"})


def _kcov(root: Path, hits: str = "1") -> bytes:
    """Mirror kcov's Cobertura writer: constant branch fields and no branch total."""
    return (
        '<?xml version="1.0" ?><coverage line-rate="0.500" lines-covered="1" lines-valid="2"'
        ' branch-rate="1.0" branches-covered="1.0" branches-rate="1.0" complexity="1.0"'
        f' version="1.9" timestamp="1"><sources><source>{root}/</source></sources>'
        '<packages><package name="run"><classes>'
        '<class name="run_sh__0" filename="bin/run.sh"><methods/><lines>'
        f'<line number="2" hits="{hits}"/><line number="3" hits="0"/></lines></class>'
        "</classes></package></packages></coverage>"
    ).encode()


def test_cobertura_reads_kcov_line_counts_without_branch_totals(tmp_path: Path) -> None:
    """A producer that measures no branches still reports its executed lines."""
    report = coverage_stream_report(
        _kcov(tmp_path),
        include_files=True,
        repository_root=tmp_path.resolve(),
        source_paths=tuple(sorted(_TRACKED)),
    )
    assert report["covered"] == 1
    assert report["total"] == 2
    assert report["files"] == {"bin/run.sh": {"lines": 2, "hit_lines": 1}}


def test_cobertura_rejects_a_declared_branch_total_that_is_not_a_count(tmp_path: Path) -> None:
    """A declared branch total keeps its integer meaning."""
    payload = _kcov(tmp_path).replace(b'complexity="1.0"', b'branches-valid="1.0"')
    with pytest.raises(ValueError, match=r"^coverage_count_invalid$"):
        coverage_stream_report(payload)


def test_lcov_merges_records_into_tracked_line_counts(tmp_path: Path) -> None:
    """Records for one file from several tests add their hits per line."""
    payload = (
        "TN:first\nSF:bin/run.sh\nDA:2,1\nDA:3,0\nLF:2\nLH:1\nend_of_record\n"
        f"TN:second\nSF:{tmp_path}/bin/run.sh\nDA:3,4,checksum\nBRDA:3,0,0,1\nend_of_record\n"
        "SF:./lib/util.sh\nDA:1,0\nend_of_record\n"
    ).encode()
    files = lcov_files(payload, repository_root=tmp_path.resolve(), tracked_paths=_TRACKED)
    assert files == {
        "bin/run.sh": {"lines": 2, "hit_lines": 2},
        "lib/util.sh": {"lines": 1, "hit_lines": 0},
    }


@pytest.mark.parametrize(
    ("payload", "gap"),
    [
        (b"", "lcov_files_missing"),
        (b"\xff", "lcov_invalid"),
        (b"DA:1,1\n", "lcov_invalid"),
        (b"SF:bin/run.sh\nDA:1,1\n", "lcov_record_unterminated"),
        (b"SF:bin/run.sh\nSF:lib/util.sh\n", "lcov_record_unterminated"),
        (b"SF:bin/run.sh\nDA:one,1\nend_of_record\n", "lcov_line_invalid"),
        (b"SF:bin/run.sh\nDA:1,-1\nend_of_record\n", "lcov_line_invalid"),
        (b"SF:bin/run.sh\nDA:1,1\nLH:0\nend_of_record\n", "lcov_count_mismatch"),
        (b"SF:bin/run.sh\nnot a record\nend_of_record\n", "lcov_invalid"),
        (b"SF:../run.sh\nDA:1,1\nend_of_record\n", "coverage_file_invalid"),
        (b"SF:/elsewhere/run.sh\nDA:1,1\nend_of_record\n", "coverage_source_outside_repository"),
        (b"SF:bin/other.sh\nDA:1,1\nend_of_record\n", "coverage_file_unbound"),
    ],
)
def test_lcov_rejects_malformed_or_unbound_records(
    tmp_path: Path, payload: bytes, gap: str
) -> None:
    """Coverage outside, beside or without exact tracked identities proves nothing."""
    with pytest.raises(ValueError, match=f"^{gap}$"):
        lcov_files(payload, repository_root=tmp_path.resolve(), tracked_paths=_TRACKED)


def _sarif(**run: object) -> bytes:
    document = {
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": "linter", "rules": [{"id": "N1"}]}}, **run}],
    }
    return json.dumps(document).encode()


def _result(root: Path, **fields: object) -> dict[str, object]:
    location = {"physicalLocation": {"artifactLocation": {"uri": f"file://{root}/bin/run.sh"}}}
    return {"ruleId": "N1", "message": {"text": "finding"}, "locations": [location], **fields}


def test_sarif_inventory_lists_analysis_targets_inside_the_repository(tmp_path: Path) -> None:
    """Analyzed artifacts become scope; results and other roles do not."""
    root = tmp_path.resolve()
    artifacts = [
        {"location": {"uri": f"file://{root}/bin/run.sh"}, "roles": ["analysisTarget"]},
        {"location": {"uri": "lib/util.sh", "uriBaseId": "%SRCROOT%"}},
        {"location": {"uri": "lib/util.sh"}, "roles": ["resultFile"]},
        {"location": {"uri": "file:///elsewhere/run.sh"}},
    ]
    report = sarif_report(
        _sarif(results=[], artifacts=artifacts), repository_root=root, tracked_paths=_TRACKED
    )
    assert report.inventory == frozenset({"bin/run.sh", "lib/util.sh"})
    assert report.findings == ()
    assert report.failures == ()


def test_sarif_without_artifacts_has_unknown_scope(tmp_path: Path) -> None:
    """A clean file leaves no result, so results never establish what was read."""
    root = tmp_path.resolve()
    report = sarif_report(
        _sarif(results=[_result(root, level="note")]),
        repository_root=root,
        tracked_paths=_TRACKED,
    )
    assert report.inventory is None
    assert report.findings == ()


@pytest.mark.parametrize(
    ("fields", "rule", "adverse"),
    [
        ({"level": "error"}, {}, True),
        ({"level": "warning"}, {}, True),
        ({}, {}, True),
        ({}, {"defaultConfiguration": {"level": "note"}}, False),
        ({"ruleIndex": 0}, {"defaultConfiguration": {"level": "error"}}, True),
        ({"level": "note"}, {}, False),
        ({"kind": "pass"}, {}, False),
        ({"kind": "informational", "level": "none"}, {}, False),
    ],
)
def test_sarif_findings_follow_kind_and_effective_level(
    tmp_path: Path, fields: dict[str, object], rule: dict[str, object], *, adverse: bool
) -> None:
    """A fail result defaults to its rule's level, then to warning; notes stay informational."""
    root = tmp_path.resolve()
    document = json.loads(_sarif(results=[_result(root, **fields)]))
    document["runs"][0]["tool"]["driver"]["rules"][0].update(rule)
    report = sarif_report(
        json.dumps(document).encode(), repository_root=root, tracked_paths=_TRACKED
    )
    assert bool(report.findings) is adverse
    if adverse:
        assert report.findings[0]["paths"] == ["bin/run.sh"]


@pytest.mark.parametrize(
    "invocation",
    [
        {"executionSuccessful": False},
        {"executionSuccessful": True, "toolExecutionNotifications": [{"message": {"text": "x"}}]},
        {
            "executionSuccessful": True,
            "toolConfigurationNotifications": [{"level": "error", "message": {"text": "x"}}],
        },
    ],
)
def test_sarif_failed_runs_and_adverse_notifications_block(
    tmp_path: Path, invocation: dict[str, object]
) -> None:
    """A tool that failed or warned about its own run cannot report a clean scan."""
    root = tmp_path.resolve()
    report = sarif_report(
        _sarif(results=[], invocations=[invocation]),
        repository_root=root,
        tracked_paths=_TRACKED,
    )
    assert report.failures


@pytest.mark.parametrize(
    ("payload", "gap"),
    [
        (b"{", "sarif_invalid"),
        (b'{"version": "2.0.0", "runs": []}', "sarif_invalid"),
        (b'{"version": "2.1.0", "runs": []}', "sarif_invalid"),
        (
            b'{"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "x"}}}]}',
            "sarif_results_missing",
        ),
        (b'{"version": "2.1.0", "runs": [{"results": []}]}', "sarif_invalid"),
        (
            (
                b'{"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "x"}},'
                b' "results": [{"level": "fatal"}]}]}'
            ),
            "sarif_invalid",
        ),
    ],
)
def test_sarif_rejects_malformed_logs(tmp_path: Path, payload: bytes, gap: str) -> None:
    """Only a complete SARIF 2.1.0 log can say a scan found nothing."""
    with pytest.raises(ValueError, match=f"^{gap}$"):
        sarif_report(payload, repository_root=tmp_path.resolve(), tracked_paths=_TRACKED)
