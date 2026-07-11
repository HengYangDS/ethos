from __future__ import annotations

import hashlib
import json

from ethos.repository.policy.performance.core import performance_quality_report


POLICY = """
schema_version = 2
latest_path = "build/evidence/quality/performance/latest.json"
baseline_path = "build/evidence/quality/performance/baseline.json"

[[commands]]
argv = ["status", "--json", "--compact"]
max_json_bytes = 4096
max_token_estimate = 1024
max_cold_regression_ratio = 1.25
max_hot_p95_regression_ratio = 1.25
""".lstrip()


def _write_policy(root, text: str = POLICY) -> str:
    path = root / ".config/checks/performance/policy.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _measurement(*, cold: float = 100, hot_p95: float = 50, bytes_: int = 100) -> dict[str, object]:
    return {
        "command": "ethos status --json --compact",
        "cold_milliseconds": cold,
        "hot_median_milliseconds": hot_p95 - 5,
        "hot_p95_milliseconds": hot_p95,
        "json_bytes": bytes_,
        "token_estimate": (bytes_ + 3) // 4,
    }


def _evidence(*, head: str, digest: str, measurement: dict[str, object], machine: str = "host-a"):
    return {
        "schema_version": 2,
        "head": head,
        "policy_digest": digest,
        "machine": {"fingerprint": machine},
        "measurements": [measurement],
    }


def _write_evidence(root, name: str, payload: dict[str, object]) -> None:
    path = root / f"build/evidence/quality/performance/{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_performance_report_accepts_same_machine_bounded_regression(tmp_path) -> None:
    digest = _write_policy(tmp_path)
    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest=digest, measurement=_measurement()),
    )
    _write_evidence(
        tmp_path,
        "latest",
        _evidence(
            head="current",
            digest=digest,
            measurement=_measurement(cold=120, hot_p95=60),
        ),
    )

    report = performance_quality_report(tmp_path, current_head="current")

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["summary"] == {
        "command_count": 1,
        "measurement_count": 1,
        "comparison": "available",
        "max_cold_milliseconds": 120.0,
        "max_hot_p95_milliseconds": 60.0,
        "max_json_bytes": 100,
        "max_token_estimate": 25,
    }
    assert report["required_gaps"] == []
    assert report["advisory_gaps"] == []


def test_performance_report_blocks_stale_latest_and_budget_regressions(
    tmp_path,
) -> None:
    digest = _write_policy(tmp_path)
    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest=digest, measurement=_measurement()),
    )
    _write_evidence(
        tmp_path,
        "latest",
        _evidence(
            head="stale",
            digest=digest,
            measurement=_measurement(cold=130, hot_p95=70, bytes_=5000),
        ),
    )

    report = performance_quality_report(tmp_path, current_head="current")

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [
        "performance_latest_head_stale:stale!=current",
        "performance_json_bytes_budget_exceeded:ethos status --json --compact:5000>4096",
        "performance_token_budget_exceeded:ethos status --json --compact:1250>1024",
        "performance_cold_regression:ethos status --json --compact:1.300>1.250",
        "performance_hot_p95_regression:ethos status --json --compact:1.400>1.250",
    ]


def test_performance_report_treats_missing_or_incompatible_baseline_as_advisory(
    tmp_path,
) -> None:
    digest = _write_policy(tmp_path)
    _write_evidence(
        tmp_path,
        "latest",
        _evidence(head="current", digest=digest, measurement=_measurement()),
    )

    missing = performance_quality_report(tmp_path, current_head="current")

    assert missing["ok"] is True
    assert missing["state"] == "advisory"
    assert missing["summary"]["comparison"] == "advisory"
    assert missing["advisory_gaps"] == ["performance_baseline_missing"]

    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest=digest, measurement=_measurement(), machine="other-host"),
    )
    mismatch = performance_quality_report(tmp_path, current_head="current")

    assert mismatch["ok"] is True
    assert mismatch["state"] == "advisory"
    assert mismatch["advisory_gaps"] == ["performance_baseline_machine_mismatch"]


def test_performance_report_treats_missing_first_capture_as_advisory(tmp_path) -> None:
    _write_policy(tmp_path)

    report = performance_quality_report(tmp_path, current_head="current")

    assert report["ok"] is True
    assert report["state"] == "advisory"
    assert report["summary"]["comparison"] == "unavailable"
    assert report["required_gaps"] == []
    assert report["advisory_gaps"] == ["performance_latest_missing"]


def test_performance_report_blocks_invalid_latest_but_advises_invalid_baseline(
    tmp_path,
) -> None:
    digest = _write_policy(tmp_path)
    latest_path = tmp_path / "build/evidence/quality/performance/latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text("{", encoding="utf-8")

    invalid_latest = performance_quality_report(tmp_path, current_head="current")

    assert invalid_latest["ok"] is False
    assert invalid_latest["required_gaps"] == ["performance_latest_invalid_json"]

    _write_evidence(
        tmp_path,
        "latest",
        _evidence(head="current", digest=digest, measurement=_measurement()),
    )
    baseline_path = tmp_path / "build/evidence/quality/performance/baseline.json"
    baseline_path.write_text("{", encoding="utf-8")

    invalid_baseline = performance_quality_report(tmp_path, current_head="current")

    assert invalid_baseline["ok"] is True
    assert invalid_baseline["state"] == "advisory"
    assert invalid_baseline["advisory_gaps"] == ["performance_baseline_invalid"]
