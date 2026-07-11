from __future__ import annotations

import hashlib
import json

import ethos.repository.policy.performance.core as performance_core
from ethos.repository.policy.performance.core import DEFAULT_LATEST_PATH
from ethos.repository.policy.performance.core import POLICY_PATH
from ethos.repository.policy.performance.core import _command_name
from ethos.repository.policy.performance.core import _command_valid
from ethos.repository.policy.performance.core import _commands
from ethos.repository.policy.performance.core import _machine_fingerprint
from ethos.repository.policy.performance.core import _maximum
from ethos.repository.policy.performance.core import _measurements
from ethos.repository.policy.performance.core import _path
from ethos.repository.policy.performance.core import _policy_digest
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


def test_performance_report_blocks_stale_latest(
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
    assert report["required_gaps"] == ["performance_latest_head_stale:stale!=current"]


def test_performance_report_blocks_output_budget_and_regression(tmp_path) -> None:
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
            measurement=_measurement(cold=130, hot_p95=70, bytes_=5000),
        ),
    )

    report = performance_quality_report(tmp_path, current_head="current")

    assert report["required_gaps"] == [
        "performance_json_bytes_budget_exceeded:ethos status --json --compact:5000>4096",
        "performance_token_budget_exceeded:ethos status --json --compact:1250>1024",
    ]

    _write_evidence(
        tmp_path,
        "latest",
        _evidence(
            head="current",
            digest=digest,
            measurement=_measurement(cold=130, hot_p95=70),
        ),
    )
    regression = performance_quality_report(tmp_path, current_head="current")

    assert regression["required_gaps"] == [
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


def test_performance_policy_and_binding_failures_are_explicit(tmp_path, monkeypatch) -> None:
    missing = performance_quality_report(tmp_path, current_head="current")
    assert (
        "performance_policy_missing:.config/checks/performance/policy.toml"
        in missing["required_gaps"]
    )

    _write_policy(tmp_path, "{")
    assert (
        "performance_policy_invalid_toml:.config/checks/performance/policy.toml"
        in (performance_quality_report(tmp_path, current_head="current")["required_gaps"])
    )

    _write_policy(tmp_path, "schema_version = 1\ncommands = []\n")
    invalid_schema = performance_quality_report(tmp_path, current_head="current")
    assert "performance_policy_schema_version_invalid" in invalid_schema["required_gaps"]
    assert "performance_policy_commands_missing" in invalid_schema["required_gaps"]

    _write_policy(
        tmp_path,
        POLICY.replace('argv = ["status", "--json", "--compact"]', "argv = []"),
    )
    invalid_command = performance_quality_report(tmp_path, current_head="current")
    assert "performance_policy_command_invalid:0" in invalid_command["required_gaps"]

    monkeypatch.setattr(performance_core.tomllib, "loads", lambda _text: [])
    assert (
        "performance_policy_invalid:.config/checks/performance/policy.toml"
        in (performance_quality_report(tmp_path, current_head="current")["required_gaps"])
    )


def test_performance_report_rejects_malformed_measurements_and_bindings(tmp_path) -> None:
    digest = _write_policy(tmp_path)
    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest=digest, measurement=_measurement()),
    )
    _write_evidence(
        tmp_path,
        "latest",
        {
            "schema_version": 2,
            "head": "current",
            "policy_digest": digest,
            "machine": {"fingerprint": "host-a"},
            "measurements": "not-a-list",
        },
    )

    missing_measurement = performance_quality_report(tmp_path, current_head="current")

    assert missing_measurement["required_gaps"] == [
        "performance_measurement_missing:ethos status --json --compact"
    ]

    invalid_metric = _measurement()
    invalid_metric["json_bytes"] = True
    _write_evidence(
        tmp_path,
        "latest",
        _evidence(head="current", digest=digest, measurement=invalid_metric),
    )
    metric_report = performance_quality_report(tmp_path, current_head="current")
    assert (
        "performance_measurement_metric_missing:ethos status --json --compact:json_bytes"
        in (metric_report["required_gaps"])
    )

    _write_evidence(tmp_path, "latest", {"schema_version": 1})
    assert performance_quality_report(tmp_path, current_head="current")["required_gaps"] == [
        "performance_latest_schema_invalid"
    ]

    _write_evidence(
        tmp_path,
        "latest",
        {
            **_evidence(head="current", digest="stale", measurement=_measurement()),
            "machine": {},
        },
    )
    assert performance_quality_report(tmp_path, current_head="current")["required_gaps"] == [
        "performance_latest_policy_stale",
        "performance_latest_machine_missing",
    ]


def test_performance_report_classifies_baseline_and_regression_edge_cases(tmp_path) -> None:
    digest = _write_policy(tmp_path)
    latest = _evidence(head="current", digest=digest, measurement=_measurement())
    _write_evidence(tmp_path, "latest", latest)

    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest="stale", measurement=_measurement()),
    )
    assert performance_quality_report(tmp_path, current_head="current")["advisory_gaps"] == [
        "performance_baseline_policy_stale"
    ]

    _write_evidence(
        tmp_path,
        "baseline",
        {
            "schema_version": 2,
            "head": "old",
            "policy_digest": digest,
            "machine": {"fingerprint": "host-a"},
            "measurements": [],
        },
    )
    assert performance_quality_report(tmp_path, current_head="current")["advisory_gaps"] == [
        "performance_baseline_measurements_missing"
    ]

    baseline_measurement = _measurement()
    baseline_measurement["command"] = "ethos other --json"
    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest=digest, measurement=baseline_measurement),
    )
    assert performance_quality_report(tmp_path, current_head="current")["required_gaps"] == [
        "performance_baseline_measurement_missing:ethos status --json --compact"
    ]

    _write_evidence(
        tmp_path,
        "baseline",
        _evidence(head="old", digest=digest, measurement=_measurement(cold=0)),
    )
    assert (
        "performance_regression_metric_invalid:ethos status --json --compact:cold_milliseconds"
        in (performance_quality_report(tmp_path, current_head="current")["required_gaps"])
    )


def test_performance_helpers_keep_defaults_and_reject_boolean_budgets() -> None:
    command = {
        "argv": ["status"],
        "max_json_bytes": True,
        "max_token_estimate": 1,
        "max_cold_regression_ratio": 1,
        "max_hot_p95_regression_ratio": 1,
    }

    assert _command_valid(command) is False
    assert _commands({"commands": "invalid"}) == []
    assert _measurements("invalid") == []
    assert _path({}, "latest_path", DEFAULT_LATEST_PATH) == DEFAULT_LATEST_PATH
    assert _path({"latest_path": 1}, "latest_path", DEFAULT_LATEST_PATH) == DEFAULT_LATEST_PATH
    assert _machine_fingerprint({"machine": "invalid"}) == ""
    assert _command_name({}) == "ethos "
    assert _maximum([], "json_bytes") is None
    assert _policy_digest(POLICY_PATH.parent / "missing.toml") == ""
