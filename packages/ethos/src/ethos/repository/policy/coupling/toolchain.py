"""Product-toolchain coupling helpers."""

from __future__ import annotations

from ethos.repository.policy.coupling.contracts import PRODUCT_REPOSITORY_GATES
from ethos.repository.policy.gates import gate_registry


def gate_profile_gaps() -> list[str]:
    """Return gaps when product repository gates drift from toolchain policy."""
    registry = gate_registry()
    gaps = []
    for gate_id in PRODUCT_REPOSITORY_GATES:
        gate = registry[gate_id]
        if gate.profile != "product-toolchain":
            gaps.append(f"gate_profile_mismatch:{gate_id}:{gate.profile}")
        if gate.toolchain != "uv-python":
            gaps.append(f"gate_toolchain_mismatch:{gate_id}:{gate.toolchain}")
    return gaps


def product_toolchain() -> dict[str, object]:
    """Return machine-readable product-toolchain binding metadata."""
    registry = gate_registry()
    toolchains = sorted({registry[gate_id].toolchain for gate_id in PRODUCT_REPOSITORY_GATES})
    return {
        "profile": "product-toolchain",
        "layer": "product_toolchain_binding",
        "gates": list(PRODUCT_REPOSITORY_GATES),
        "toolchains": toolchains,
        "product_ontology_anchor": False,
    }
