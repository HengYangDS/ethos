from __future__ import annotations

from ethos_governance.standards import standard_adapter_registry


def test_standard_adapter_registry_is_explicit_and_retirable() -> None:
    registry = standard_adapter_registry()

    assert registry["slsa"]["mode"] == "native-standard"
    assert registry["in_toto"]["mode"] == "attestation-envelope"
    assert registry["sigstore"]["mode"] == "first-class-adapter"
    assert registry["spdx"]["mode"] == "artifact-metadata-adapter"
    assert registry["cdevents"]["mode"] == "event-interchange-adapter"
    assert registry["opentelemetry"]["mode"] == "native-standard"
    assert registry["dagger"]["mode"] == "runner-adapter"
    assert registry["cue"]["mode"] == "advanced-compiler"
    assert registry["opa"]["mode"] == "policy-adapter"
    assert registry["temporal"]["mode"] == "service-runtime-adapter"
    assert registry["mcp"]["mode"] == "agent-projection"
    for item in registry.values():
        assert item["lifecycle"] in {"native", "adapter", "optional", "experimental"}
        assert item["input_contract"]
        assert item["output_contract"]
        assert item["fallback"]
        assert item["exit_strategy"]
