from __future__ import annotations

import ethos.repository.policy.performance.core as performance_core
from tests.support.ethos_cli_runner import run_ethos


def test_quality_performance_projects_a_machine_local_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        performance_core,
        "performance_quality_report",
        lambda _root, *, current_head: {
            "ok": True,
            "state": "advisory",
            "summary": {
                "command_count": 2,
                "measurement_count": 0,
                "comparison": "unavailable",
                "max_cold_milliseconds": None,
                "max_hot_p95_milliseconds": None,
                "max_json_bytes": None,
                "max_token_estimate": None,
            },
            "required_gaps": [],
            "advisory_gaps": ["performance_latest_missing"],
            "current_head": current_head,
        },
    )

    payload = run_ethos("quality", "performance", "--json")

    assert payload["ok"] is True
    assert payload["state"] == "advisory"
    assert payload["summary"]["comparison"] == "unavailable"
    assert payload["data"]["advisory_gaps"] == ["performance_latest_missing"]
