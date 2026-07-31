"""Quality gate projections compiled from the tracked gate declaration."""

from __future__ import annotations

from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration


def quality_gate_registry() -> dict[str, Gate]:
    """Return the immutable quality descriptor view of the gate declaration."""
    return load_gate_registry_declaration().registry("quality")


QUALITY_GATES = tuple(quality_gate_registry().values())


def product_gate_plan() -> dict[str, object]:
    """Project quality descriptors to the stable quality gate plan contract."""
    return {
        "schema_version": 1,
        "gates": [gate.to_dict() for gate in QUALITY_GATES],
    }
