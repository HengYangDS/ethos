from __future__ import annotations

from tests.support.ethos_cli_runner import run_ethos


def test_quality_generated_artifacts_command_reports_contract() -> None:
    payload = run_ethos("quality", "generated-artifacts", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality generated-artifacts"
    assert payload["state"] == "clean"
    declarative = {item["prefix"] for item in payload["data"]["contract"]["declarative_prefixes"]}
    assert declarative == {".config/ethos"}
    allowed = {item["prefix"] for item in payload["data"]["contract"]["allowed_prefixes"]}
    assert {"build/ethos", "build/evidence", ".cache/local-state"} <= allowed
    denied = {item["prefix"] for item in payload["data"]["contract"]["denied_generated_prefixes"]}
    assert ".config" in denied
