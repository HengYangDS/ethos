"""Product-toolchain coupling helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.gates import gate_registry

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.registry.declarations import CouplingDeclaration


def gate_profile_gaps(root: Path, declaration: CouplingDeclaration) -> list[str]:
    """Return gaps when product repository gates drift from toolchain policy."""
    registry = gate_registry(root)
    gates = declaration.product_repository_gates
    gaps = []
    for gate_id in gates:
        gate = registry[gate_id]
        if gate.profile != "product-toolchain":
            gaps.append(f"gate_profile_mismatch:{gate_id}:{gate.profile}")
        if gate.toolchain != "uv-python":
            gaps.append(f"gate_toolchain_mismatch:{gate_id}:{gate.toolchain}")
    return gaps


def product_toolchain(root: Path, declaration: CouplingDeclaration) -> dict[str, object]:
    """Return machine-readable product-toolchain binding metadata."""
    registry = gate_registry(root)
    gates = declaration.product_repository_gates
    return {
        "profile": "product-toolchain",
        "layer": "product_toolchain_binding",
        "gates": list(gates),
        "toolchains": sorted({registry[gate_id].toolchain for gate_id in gates}),
        "product_ontology_anchor": False,
    }
