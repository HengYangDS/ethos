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
    assert {
        "build/runtime/tool-cache",
        "build/runtime/work",
        "build/ethos",
        "build/evidence",
        "build/artifacts",
        ".cache/local-state",
    } <= allowed
    denied = {item["prefix"] for item in payload["data"]["contract"]["denied_generated_prefixes"]}
    denied_static = {item["prefix"] for item in payload["data"]["contract"]["denied_prefixes"]}
    denied_root_cache = {
        item["prefix"] for item in payload["data"]["contract"]["denied_root_cache_prefixes"]
    }
    denied_legacy = {
        item["prefix"] for item in payload["data"]["contract"]["denied_legacy_generated_prefixes"]
    }
    review = {item["prefix"] for item in payload["data"]["contract"]["review_prefixes"]}
    assert ".config" in denied
    assert "docs" in denied
    assert ".config/ci/scripts" in denied_static
    assert ".import_linter_cache" in denied_root_cache
    assert "build/cache" in denied_legacy
    assert "dist" in denied_legacy
    assert "tools/ci/scripts" in review
