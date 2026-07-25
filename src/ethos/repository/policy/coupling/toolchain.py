"""Product-toolchain coupling helpers."""

from __future__ import annotations

from ethos.contracts.registry.declarations import load_coupling_declaration
from ethos.repository.policy.gates import gate_registry


def gate_profile_gaps() -> list[str]:
    """Return gaps when product repository gates drift from toolchain policy."""
    registry = gate_registry()
    gates = load_coupling_declaration().product_repository_gates
    gaps = []
    for gate_id in gates:
        gate = registry[gate_id]
        if gate.profile != "product-toolchain":
            gaps.append(f"gate_profile_mismatch:{gate_id}:{gate.profile}")
        if gate.toolchain != "uv-python":
            gaps.append(f"gate_toolchain_mismatch:{gate_id}:{gate.toolchain}")
    return gaps


def product_toolchain() -> dict[str, object]:
    """Return machine-readable product-toolchain binding metadata."""
    registry = gate_registry()
    gates = load_coupling_declaration().product_repository_gates
    return {
        "profile": "product-toolchain",
        "layer": "product_toolchain_binding",
        "gates": list(gates),
        "toolchains": sorted({registry[gate_id].toolchain for gate_id in gates}),
        "product_ontology_anchor": False,
    }
