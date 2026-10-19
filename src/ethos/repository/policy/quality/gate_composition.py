"""Compose applicable shared proof floors with repository-native increments."""

from __future__ import annotations

from pathlib import Path

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.repository.policy.rules.config import path_matches


def select_gate_declaration(
    declaration: GateRegistryDeclaration,
    gate_ids: tuple[str, ...],
    packaged_declaration: GateRegistryDeclaration,
    *,
    repository_paths: tuple[str, ...] = (),
    full: bool = False,
) -> GateRegistryDeclaration:
    """Compose applicable shared floors and native increments; explicit diagnosis stays focused."""
    owned = declaration.registry()
    packaged = packaged_declaration.registry()
    authored = tuple(
        path
        for path in repository_paths
        if not path.startswith(("evidence/", "docs/archive/", "openspec/changes/archive/"))
    )
    common = tuple(
        gate.id
        for gate in packaged.values()
        if gate.required_for_paths
        and (
            gate.id in gate_ids
            or (
                (full or not gate_ids)
                and any(path_matches(path, gate.required_for_paths) for path in authored)
            )
        )
    )
    execution_fields = {
        "command",
        "providers",
        "verification_providers",
        "depends_on",
        "native_outputs",
    }
    for gate_id in common:
        if gate_id in owned and owned[gate_id].model_dump(include=execution_fields) != (
            packaged[gate_id].model_dump(include=execution_fields)
        ):
            message = f"common_gate_execution_conflict:{gate_id}"
            raise ValueError(message)
    common_contracts = {
        gate_id: packaged[gate_id].model_copy(
            update={"profile": "repository", "tool_adapter": "ethos"}
        )
        for gate_id in common
    }
    extra: dict[str, Gate] = {}
    pending = [*common, *gate_ids]
    while pending:
        gate_id = pending.pop()
        if gate_id in owned or gate_id in extra:
            continue
        gate = packaged.get(gate_id)
        if gate is None:
            message = "unknown proof gate"
            raise ValueError(message)
        extra[gate_id] = (
            gate.model_copy(update={"profile": "repository", "tool_adapter": "ethos"})
            if gate.providers or gate.verification_providers
            else gate
        )
        pending.extend(gate.depends_on)
    proof_sets = GateProofSets(
        default=tuple(dict.fromkeys((*declaration.proof_sets.default, *common))),
        full=tuple(dict.fromkeys((*declaration.proof_sets.full, *common))),
    )
    gates = tuple(common_contracts.get(gate.id, gate) for gate in declaration.gates)
    if not extra and gates == declaration.gates and proof_sets == declaration.proof_sets:
        return declaration
    return GateRegistryDeclaration(
        id=declaration.id,
        schema_version=declaration.schema_version,
        source_refs=declaration.source_refs,
        proof_sets=proof_sets,
        gates=(*gates, *extra.values()),
    )


def canonical_gate_command(command: tuple[str, ...]) -> tuple[str, ...]:
    """Remove only a host-specific absolute Python interpreter path."""
    if not command:
        return command
    head, *rest = command
    name = Path(head).name
    return ("python", *rest) if Path(head).is_absolute() and name.startswith("python") else command
