"""Python coverage quality read model."""

from __future__ import annotations

import configparser
import tomllib
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as DefusedET
from defusedxml.ElementTree import ParseError

COVERAGE_CONFIG_DIR = Path(".config/checks/coverage")
COVERAGE_EVIDENCE_DIR = Path("build/evidence/quality/tests/coverage")
POLICY_PATH = COVERAGE_CONFIG_DIR / "policy.toml"
CONFIG_PATH = COVERAGE_CONFIG_DIR / "coverage.ini"
ARTIFACT_PATH = COVERAGE_EVIDENCE_DIR / "coverage.xml"
OWNER_SCRIPT = ".config/ci/scripts/run-python-tests.sh"


def coverage_quality_report(root: Path) -> dict[str, object]:
    """Report configured and latest Python coverage state without running tests."""
    policy, policy_gaps = _load_policy(root / POLICY_PATH)
    config, config_gaps = _load_config(root / CONFIG_PATH)
    artifact, artifact_gaps = _load_artifact(root / ARTIFACT_PATH)
    gaps = [*policy_gaps, *config_gaps, *artifact_gaps]

    hard_floor = _number(policy.get("current_hard_floor"))
    branch_required = bool(policy.get("branch_coverage_required", False))
    fail_under = _number(config.get("fail_under"))
    branch_enabled = bool(config.get("branch", False))
    latest_percent = _number(artifact.get("line_percent"))

    if hard_floor is not None and fail_under is not None and fail_under != hard_floor:
        gaps.append(f"coverage_fail_under_mismatch:{fail_under:g}!={hard_floor:g}")
    if branch_required and not branch_enabled:
        gaps.append("coverage_branch_disabled")
    if hard_floor is not None and latest_percent is not None and latest_percent < hard_floor:
        gaps.append(f"coverage_latest_below_floor:{latest_percent:.2f}<{hard_floor:.2f}")

    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "policy": {
            "path": POLICY_PATH.as_posix(),
            "current_hard_floor": hard_floor,
            "aspirational_floor": _number(policy.get("aspirational_floor")),
            "branch_coverage_required": branch_required,
            "owner": str(policy.get("owner") or ""),
            "source": str(policy.get("source") or ""),
        },
        "config": {
            "path": CONFIG_PATH.as_posix(),
            "fail_under": fail_under,
            "branch": branch_enabled,
            "source": list(config.get("source", [])),
        },
        "owner_script": OWNER_SCRIPT,
        "latest_artifact": artifact,
        "required_gaps": gaps,
    }


def _load_policy(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        return dict(tomllib.loads(path.read_text(encoding="utf-8"))), []
    except FileNotFoundError:
        return {}, [f"coverage_policy_missing:{POLICY_PATH.as_posix()}"]
    except tomllib.TOMLDecodeError:
        return {}, [f"coverage_policy_invalid_toml:{POLICY_PATH.as_posix()}"]


def _load_config(path: Path) -> tuple[dict[str, Any], list[str]]:
    parser = configparser.ConfigParser()
    if not path.exists():
        return {}, [f"coverage_config_missing:{CONFIG_PATH.as_posix()}"]
    parser.read(path, encoding="utf-8")
    gaps: list[str] = []
    if not parser.has_section("run"):
        gaps.append("coverage_config_missing_section:run")
    if not parser.has_section("report"):
        gaps.append("coverage_config_missing_section:report")
    source = _multiline_option(parser, "run", "source")
    fail_under = parser.get("report", "fail_under", fallback="")
    return {
        "branch": parser.getboolean("run", "branch", fallback=False),
        "source": source,
        "fail_under": _parse_number(fail_under),
    }, gaps


def _load_artifact(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {
            "path": ARTIFACT_PATH.as_posix(),
            "present": False,
        }, [f"coverage_artifact_missing:{ARTIFACT_PATH.as_posix()}"]
    try:
        root = DefusedET.parse(path).getroot()
    except ParseError:
        return {
            "path": ARTIFACT_PATH.as_posix(),
            "present": True,
        }, [f"coverage_artifact_malformed:{ARTIFACT_PATH.as_posix()}"]
    line_rate = _parse_number(root.attrib.get("line-rate", ""))
    branch_rate = _parse_number(root.attrib.get("branch-rate", ""))
    lines_valid = _parse_number(root.attrib.get("lines-valid", ""))
    lines_covered = _parse_number(root.attrib.get("lines-covered", ""))
    return {
        "path": ARTIFACT_PATH.as_posix(),
        "present": True,
        "line_rate": line_rate,
        "branch_rate": branch_rate,
        "line_percent": None if line_rate is None else round(line_rate * 100, 2),
        "branch_percent": None if branch_rate is None else round(branch_rate * 100, 2),
        "lines_valid": lines_valid,
        "lines_covered": lines_covered,
    }, []


def _multiline_option(parser: configparser.ConfigParser, section: str, option: str) -> list[str]:
    value = parser.get(section, option, fallback="")
    return [line.strip() for line in value.splitlines() if line.strip()]


def _parse_number(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str) or not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _number(value: object) -> float | None:
    return _parse_number(value)
