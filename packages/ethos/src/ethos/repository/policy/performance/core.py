"""Read local command-performance evidence without making it repository truth."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

POLICY_PATH = Path(".config/checks/performance/policy.toml")
DEFAULT_LATEST_PATH = Path("build/evidence/quality/performance/latest.json")
DEFAULT_BASELINE_PATH = Path("build/evidence/quality/performance/baseline.json")
_ABSOLUTE_BUDGETS = (
    ("json_bytes", "max_json_bytes", "performance_json_bytes_budget_exceeded"),
    ("token_estimate", "max_token_estimate", "performance_token_budget_exceeded"),
)
_REGRESSION_BUDGETS = (
    ("cold_milliseconds", "max_cold_regression_ratio", "performance_cold_regression"),
    (
        "hot_p95_milliseconds",
        "max_hot_p95_regression_ratio",
        "performance_hot_p95_regression",
    ),
)


def performance_quality_report(root: Path, *, current_head: str) -> dict[str, object]:
    """Report bounded output and same-machine performance-regression evidence.

    Runtime artifacts deliberately remain ignored local evidence. A missing
    capture is therefore advisory; a present latest capture must be well formed,
    current-head-bound, and policy-bound. Baseline absence or incompatibility is
    advisory because no repository checkout can manufacture another machine's
    historical timing facts.
    """
    policy, policy_gaps = _load_policy(root / POLICY_PATH)
    commands = _commands(policy)
    latest_path = _path(policy, "latest_path", DEFAULT_LATEST_PATH)
    baseline_path = _path(policy, "baseline_path", DEFAULT_BASELINE_PATH)
    latest, latest_gaps = _load_evidence(root / latest_path, label="latest")
    baseline, baseline_gaps = _load_evidence(root / baseline_path, label="baseline")
    required_gaps = list(policy_gaps)
    advisory_gaps: list[str] = []
    measurements: list[dict[str, object]] = []
    comparison = "unavailable"

    if latest_gaps:
        advisory_gaps.extend(latest_gaps if latest_gaps == ["performance_latest_missing"] else [])
        required_gaps.extend(gap for gap in latest_gaps if gap != "performance_latest_missing")
    else:
        latest_binding_gaps = _latest_binding_gaps(
            latest,
            current_head=current_head,
            policy_digest=_policy_digest(root / POLICY_PATH),
        )
        required_gaps.extend(latest_binding_gaps)
        measurements = _measurements(latest.get("measurements"))
        required_gaps.extend(_absolute_measurement_gaps(commands, measurements))
        baseline_ok, baseline_advisories = _baseline_compatibility(
            baseline,
            baseline_gaps,
            latest=latest,
            policy_digest=_policy_digest(root / POLICY_PATH),
        )
        advisory_gaps.extend(baseline_advisories)
        if baseline_ok:
            comparison = "available"
            required_gaps.extend(
                _regression_gaps(commands, latest_measurements=measurements, baseline=baseline)
            )
        elif not latest_binding_gaps:
            comparison = "advisory"

    summary = _summary(commands, measurements, comparison=comparison)
    state = "blocked" if required_gaps else "advisory" if advisory_gaps else "clean"
    return {
        "ok": not required_gaps,
        "state": state,
        "policy": {
            "path": POLICY_PATH.as_posix(),
            "digest": _policy_digest(root / POLICY_PATH),
            "latest_path": latest_path.as_posix(),
            "baseline_path": baseline_path.as_posix(),
            "commands": commands,
        },
        "evidence": {
            "latest": _evidence_summary(latest_path, latest, present=not latest_gaps),
            "baseline": _evidence_summary(baseline_path, baseline, present=not baseline_gaps),
            "comparison": comparison,
        },
        "measurements": measurements,
        "summary": summary,
        "required_gaps": required_gaps,
        "advisory_gaps": advisory_gaps,
    }


def _load_policy(path: Path) -> tuple[dict[str, Any], list[str]]:
    """Load and minimally validate the tracked policy contract."""
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"performance_policy_missing:{POLICY_PATH.as_posix()}"]
    except tomllib.TOMLDecodeError:
        return {}, [f"performance_policy_invalid_toml:{POLICY_PATH.as_posix()}"]
    if not isinstance(payload, dict):
        return {}, [f"performance_policy_invalid:{POLICY_PATH.as_posix()}"]
    gaps: list[str] = []
    if payload.get("schema_version") != 2:
        gaps.append("performance_policy_schema_version_invalid")
    if not _commands(payload):
        gaps.append("performance_policy_commands_missing")
    for index, command in enumerate(_commands(payload)):
        if not _command_valid(command):
            gaps.append(f"performance_policy_command_invalid:{index}")
    return payload, gaps


def _load_evidence(path: Path, *, label: str) -> tuple[dict[str, Any], list[str]]:
    """Read one ignored local artifact while preserving absence semantics."""
    if not path.exists():
        return {}, [f"performance_{label}_missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, [f"performance_{label}_invalid_json"]
    if not isinstance(payload, dict) or payload.get("schema_version") != 2:
        return {}, [f"performance_{label}_schema_invalid"]
    return payload, []


def _commands(policy: dict[str, Any]) -> list[dict[str, object]]:
    """Normalize declared command specifications in stable source order."""
    raw = policy.get("commands")
    return [dict(item) for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _command_valid(command: dict[str, object]) -> bool:
    """Require an argv plus positive output and regression envelopes."""
    argv = command.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        return False
    return all(
        _positive(command.get(field))
        for field in (
            "max_json_bytes",
            "max_token_estimate",
            "max_cold_regression_ratio",
            "max_hot_p95_regression_ratio",
        )
    )


def _latest_binding_gaps(
    latest: dict[str, Any], *, current_head: str, policy_digest: str
) -> list[str]:
    """Return latest-capture bindings that must hold before it can be trusted."""
    gaps: list[str] = []
    latest_head = str(latest.get("head") or "")
    if latest_head != current_head:
        gaps.append(f"performance_latest_head_stale:{latest_head}!={current_head}")
    if str(latest.get("policy_digest") or "") != policy_digest:
        gaps.append("performance_latest_policy_stale")
    if not _machine_fingerprint(latest):
        gaps.append("performance_latest_machine_missing")
    return gaps


def _baseline_compatibility(
    baseline: dict[str, Any],
    baseline_gaps: list[str],
    *,
    latest: dict[str, Any],
    policy_digest: str,
) -> tuple[bool, list[str]]:
    """Classify baseline absence or mismatch as non-blocking local uncertainty."""
    if baseline_gaps:
        return (
            False,
            [
                "performance_baseline_missing"
                if baseline_gaps == ["performance_baseline_missing"]
                else "performance_baseline_invalid"
            ],
        )
    if str(baseline.get("policy_digest") or "") != policy_digest:
        return False, ["performance_baseline_policy_stale"]
    if _machine_fingerprint(baseline) != _machine_fingerprint(latest):
        return False, ["performance_baseline_machine_mismatch"]
    if not _measurements(baseline.get("measurements")):
        return False, ["performance_baseline_measurements_missing"]
    return True, []


def _absolute_measurement_gaps(
    commands: list[dict[str, object]], measurements: list[dict[str, object]]
) -> list[str]:
    """Check every latest measurement for its absolute reader-size envelope."""
    by_command = {_measurement_name(item): item for item in measurements}
    gaps: list[str] = []
    for command in commands:
        name = _command_name(command)
        measurement = by_command.get(name)
        if measurement is None:
            gaps.append(f"performance_measurement_missing:{name}")
            continue
        for metric, budget_name, gap_name in _ABSOLUTE_BUDGETS:
            actual = _number(measurement.get(metric))
            budget = _number(command.get(budget_name))
            if actual is None:
                gaps.append(f"performance_measurement_metric_missing:{name}:{metric}")
            elif budget is not None and actual > budget:
                gaps.append(f"{gap_name}:{name}:{int(actual)}>{int(budget)}")
    return gaps


def _regression_gaps(
    commands: list[dict[str, object]],
    *,
    latest_measurements: list[dict[str, object]],
    baseline: dict[str, Any],
) -> list[str]:
    """Compare cold and hot paths only when a compatible local baseline exists."""
    latest_by_command = {_measurement_name(item): item for item in latest_measurements}
    baseline_by_command = {
        _measurement_name(item): item for item in _measurements(baseline.get("measurements"))
    }
    gaps: list[str] = []
    for command in commands:
        name = _command_name(command)
        latest = latest_by_command.get(name)
        baseline_measurement = baseline_by_command.get(name)
        if latest is None or baseline_measurement is None:
            gaps.append(f"performance_baseline_measurement_missing:{name}")
            continue
        for metric, budget_name, gap_name in _REGRESSION_BUDGETS:
            current = _number(latest.get(metric))
            reference = _number(baseline_measurement.get(metric))
            budget = _number(command.get(budget_name))
            if current is None or reference is None or reference <= 0 or budget is None:
                gaps.append(f"performance_regression_metric_invalid:{name}:{metric}")
                continue
            ratio = current / reference
            if ratio > budget:
                gaps.append(f"{gap_name}:{name}:{ratio:.3f}>{budget:.3f}")
    return gaps


def _measurements(value: object) -> list[dict[str, object]]:
    """Normalize valid measurement mappings in source order."""
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _summary(
    commands: list[dict[str, object]],
    measurements: list[dict[str, object]],
    *,
    comparison: str,
) -> dict[str, object]:
    """Project bounded aggregate facts for CLI and agent readers."""
    return {
        "command_count": len(commands),
        "measurement_count": len(measurements),
        "comparison": comparison,
        "max_cold_milliseconds": _maximum(measurements, "cold_milliseconds"),
        "max_hot_p95_milliseconds": _maximum(measurements, "hot_p95_milliseconds"),
        "max_json_bytes": _maximum(measurements, "json_bytes"),
        "max_token_estimate": _maximum(measurements, "token_estimate"),
    }


def _evidence_summary(path: Path, evidence: dict[str, Any], *, present: bool) -> dict[str, object]:
    """Keep evidence provenance visible without echoing full ignored artifacts."""
    return {
        "path": path.as_posix(),
        "present": present,
        "head": str(evidence.get("head") or ""),
        "policy_digest": str(evidence.get("policy_digest") or ""),
        "machine_fingerprint": _machine_fingerprint(evidence),
    }


def _path(policy: dict[str, Any], key: str, default: Path) -> Path:
    """Return a declared relative artifact path or the semantic default."""
    value = policy.get(key)
    return Path(value) if isinstance(value, str) and value else default


def _policy_digest(path: Path) -> str:
    """Hash the exact tracked contract that governed a capture."""
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _machine_fingerprint(evidence: dict[str, Any]) -> str:
    """Read the opaque same-host comparison key from an evidence envelope."""
    machine = evidence.get("machine")
    return str(machine.get("fingerprint") or "") if isinstance(machine, dict) else ""


def _command_name(command: dict[str, object]) -> str:
    """Render the stable reader command identifier used in evidence."""
    argv = command.get("argv")
    items = argv if isinstance(argv, list) else []
    return "ethos " + " ".join(str(item) for item in items)


def _measurement_name(measurement: dict[str, object]) -> str:
    """Read the canonical rendered command name from one evidence measurement."""
    return str(measurement.get("command") or "")


def _maximum(measurements: list[dict[str, object]], field: str) -> float | int | None:
    """Return the numeric maximum while preserving integer size metrics."""
    numeric = [
        value for value in (_number(item.get(field)) for item in measurements) if value is not None
    ]
    if not numeric:
        return None
    maximum = max(numeric)
    return maximum if field.endswith("milliseconds") else int(maximum)


def _positive(value: object) -> bool:
    """Accept positive numeric policy values while rejecting Boolean aliases."""
    numeric = _number(value)
    return numeric is not None and numeric > 0


def _number(value: object) -> float | None:
    """Parse an integer or float metric without accepting Boolean values."""
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None
