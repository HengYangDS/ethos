from __future__ import annotations

from ethos.repository.registry.standards import standard_adapter_registry

EXPECTED_MODES = {
    "slsa": "local-projection",
    "in_toto": "local-projection",
    "sigstore": "first-class-adapter",
    "spdx": "local-projection",
    "mcp": "agent-projection",
}


def test_standard_adapter_registry_projects_declared_records() -> None:
    assert {
        adapter_id: item["mode"] for adapter_id, item in standard_adapter_registry().items()
    } == EXPECTED_MODES
    assert all(
        item["input_contract"]
        and item["output_contract"]
        and item["fallback"]
        and item["exit_strategy"]
        for item in standard_adapter_registry().values()
    )
