from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.coverage import coverage_quality_report

if TYPE_CHECKING:
    from pathlib import Path


def write_coverage_policy(root: Path, *, fail_under: int = 95, branch: bool = True) -> None:
    coverage_dir = root / ".config" / "checks" / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)
    (coverage_dir / "policy.toml").write_text(
        """current_hard_floor = 95
aspirational_floor = 95
branch_coverage_required = true
owner = "product-toolchain"
source = ".config/checks/coverage/coverage.ini and .config/ci/scripts/run-python-tests.sh"
""",
        encoding="utf-8",
    )
    (coverage_dir / "coverage.ini").write_text(
        "\n".join(
            [
                "[run]",
                f"branch = {branch!s}",
                "source =",
                "    packages/ethos/src/ethos",
                "    packages/ethos-core/src/ethos_core",
                "",
                "[report]",
                f"fail_under = {fail_under}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_coverage_xml(root: Path, *, line_rate: float = 0.96, branch_rate: float = 0.95) -> None:
    coverage_dir = root / ".config" / "checks" / "coverage"
    coverage_dir.mkdir(parents=True, exist_ok=True)
    (coverage_dir / "coverage.xml").write_text(
        (
            '<?xml version="1.0" ?>\n'
            f'<coverage line-rate="{line_rate}" branch-rate="{branch_rate}" '
            'lines-covered="96" lines-valid="100"></coverage>\n'
        ),
        encoding="utf-8",
    )


def test_coverage_quality_report_reads_policy_config_and_latest_artifact(tmp_path: Path) -> None:
    write_coverage_policy(tmp_path)
    write_coverage_xml(tmp_path)

    report = coverage_quality_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["policy"]["current_hard_floor"] == 95.0
    assert report["config"]["fail_under"] == 95.0
    assert report["config"]["branch"] is True
    assert report["config"]["source"] == [
        "packages/ethos/src/ethos",
        "packages/ethos-core/src/ethos_core",
    ]
    assert report["latest_artifact"]["line_percent"] == 96.0
    assert report["latest_artifact"]["branch_percent"] == 95.0
    assert report["owner_script"] == ".config/ci/scripts/run-python-tests.sh"


def test_coverage_quality_report_blocks_stale_or_mismatched_floor(tmp_path: Path) -> None:
    write_coverage_policy(tmp_path, fail_under=90, branch=False)
    write_coverage_xml(tmp_path, line_rate=0.94)

    report = coverage_quality_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "coverage_fail_under_mismatch:90!=95",
        "coverage_branch_disabled",
        "coverage_latest_below_floor:94.00<95.00",
    ]


def test_coverage_quality_report_reports_missing_latest_artifact(tmp_path: Path) -> None:
    write_coverage_policy(tmp_path)

    report = coverage_quality_report(tmp_path)

    assert report["ok"] is False
    assert report["latest_artifact"] == {
        "path": ".config/checks/coverage/coverage.xml",
        "present": False,
    }
    assert report["required_gaps"] == [
        "coverage_artifact_missing:.config/checks/coverage/coverage.xml"
    ]
