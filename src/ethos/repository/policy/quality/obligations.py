"""Conjoin product-owned evidence for code quality and native artifact authenticity."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TYPE_CHECKING

from pydantic import ValidationError

from ethos.contracts.value import mutable_json
from ethos.contracts.verdict import execution_succeeded
from ethos.repository.policy.quality_reports import quality_evidence_paths
from ethos.repository.profile import ProofPolicy

if TYPE_CHECKING:
    from ethos.contracts.gates import Gate
    from ethos.repository.profile import SourceContract

QUALITY_PROVIDERS = {
    "behavior": (
        "ethos.adapters.gates.python_quality:behavior_report",
        "ethos.adapters.gates.code_quality:behavior_report",
    ),
    "static-analysis": (
        "ethos.adapters.gates.python_quality:static_report",
        "ethos.adapters.gates.code_quality:static_report",
    ),
}


INTEGRITY_PROVIDER = "ethos.adapters.gates.provenance.observation:integrity_report"


def quality_obligation_gaps(
    policy: Mapping[str, object], checks: object, *, source_tree: str
) -> tuple[str, ...]:
    """Keep execution success distinct from evidence for observed code axes."""
    owner = policy.get("owner")
    if not isinstance(owner, Mapping):
        return ()
    integrity_gaps = source_integrity_gaps(policy, checks, source_tree=source_tree)
    version = owner.get("quality_floor_version")
    if version is None:
        return integrity_gaps
    if version not in (1, 2):
        return (f"quality_floor_version_unsupported:{version}",)
    axes = owner.get("code_correctness_map")
    if not isinstance(axes, Mapping) or not axes:
        return integrity_gaps
    gates = policy.get("gates")
    if not isinstance(gates, (list, tuple)) or not isinstance(checks, (list, tuple)):
        return tuple(f"quality_obligation_unproven:{axis}" for axis in axes)
    by_check = {
        check.get("action_id"): check
        for check in checks
        if isinstance(check, Mapping) and check.get("action_id")
    }
    subjects = owner.get("quality_subjects")
    gaps: list[str] = list(integrity_gaps)
    for axis, gate_id in axes.items():
        expected = subjects.get(axis) if isinstance(subjects, Mapping) else None
        valid_expected = (
            isinstance(expected, (list, tuple))
            and bool(expected)
            and all(isinstance(path, str) and path for path in expected)
            and len(set(expected)) == len(expected)
        )
        if (
            not isinstance(axis, str)
            or not isinstance(gate_id, str)
            or (version == 2 and not valid_expected)
            or (expected is not None and not valid_expected)
        ):
            gaps.append(f"quality_obligation_unproven:{axis}")
            continue
        selected = _quality_axis_gates(gates, axis, gate_id)
        observations = [
            _qualified_quality_paths(gate, by_check.get(gate.get("id")), axis, source_tree, owner)
            for gate in selected
        ]
        observed = {path for paths in observations for path in paths}
        if (
            not any(gate.get("id") == gate_id for gate in selected)
            or any(not paths for paths in observations)
            or (valid_expected and observed != set(expected))
        ):
            gaps.append(f"quality_obligation_unproven:{axis}")
    return tuple(gaps)


def _quality_axis_gates(
    gates: list[object] | tuple[object, ...], axis: str, primary: str
) -> tuple[Mapping[str, object], ...]:
    """Select the mapped gate and every declared contributor to the same axis."""
    return tuple(
        gate
        for gate in gates
        if isinstance(gate, Mapping)
        and (
            gate.get("id") == primary
            or (isinstance(gate.get("dimensions"), (list, tuple)) and axis in gate["dimensions"])
        )
    )


def quality_verifier_gaps(
    owner: Mapping[str, object], selected: tuple[dict[str, object], ...]
) -> tuple[str, ...]:
    """Reject a missing verifier before native check execution starts."""
    axes = owner.get("code_correctness_map")
    if not isinstance(axes, Mapping):
        return ()
    gaps: list[str] = []
    for axis, gate_id in axes.items():
        applicable = _quality_axis_gates(selected, axis, gate_id)
        if not any(gate.get("id") == gate_id for gate in applicable):
            gaps.append(f"quality_obligation_unproven:{axis}")
            continue
        gaps.extend(
            f"quality_gate_verifier_missing:{axis}:{gate['id']}"
            for gate in applicable
            if not _quality_provider_refs(gate, axis)
        )
    return tuple(gaps)


def _qualified_quality_paths(
    gate: object, check: object, axis: str, source_tree: str, owner: Mapping[str, object]
) -> tuple[str, ...]:
    """Read scoped paths only from the selected product-owned verifier."""
    if not isinstance(gate, Mapping) or not isinstance(check, Mapping) or not source_tree:
        return ()
    identity = gate.get("execution_identity")
    eligible = _quality_provider_refs(gate, axis)
    if not eligible or not isinstance(identity, (list, tuple)):
        return ()
    payload, providers = _quality_provider_payload(gate, check, identity)
    if not isinstance(payload, Mapping) or payload.get("gate") != gate.get("id"):
        return ()
    observations = payload.get("providers")
    if not isinstance(observations, list):
        return ()
    required = set(providers) & set(eligible)
    measured: dict[str, tuple[str, ...]] = {}
    for item in observations:
        if not isinstance(item, Mapping) or item.get("provider") not in required:
            continue
        provider = item["provider"]
        report = item.get("report")
        paths = quality_evidence_paths(report, axis, source_tree)
        valid_partition = axis != "static-analysis" or _partition_matches(report, paths, owner)
        if (
            not isinstance(provider, str)
            or provider in measured
            or not paths
            or not valid_partition
        ):
            return ()
        measured[provider] = paths
    return (
        tuple(path for paths in measured.values() for path in paths)
        if required and measured.keys() == required
        else ()
    )


def _partition_matches(report: object, paths: tuple[str, ...], owner: Mapping[str, object]) -> bool:
    """Author and artifact partitions cover the exact selected set without overlap."""
    if not isinstance(report, Mapping):
        return False
    evidence = report.get("quality_evidence")
    if not isinstance(evidence, Mapping):
        return False
    kinds = source_kinds(owner)
    expected = set(paths) & kinds.keys()
    artifacts = evidence.get("artifact_paths", [])
    authored = evidence.get("authored_paths", list(paths) if not expected else [])
    return (
        isinstance(artifacts, (list, tuple))
        and isinstance(authored, (list, tuple))
        and all(isinstance(path, str) for path in (*artifacts, *authored))
        and len(set(artifacts)) == len(artifacts)
        and len(set(authored)) == len(authored)
        and set(artifacts) == expected
        and set(authored) == set(paths) - expected
    )


def _quality_provider_refs(gate: Mapping[str, object], axis: str) -> tuple[str, ...]:
    """Identify a selected product verifier before spending time on a gate."""
    if gate.get("tool_adapter") != "ethos":
        return ()
    if gate.get("execution_mode") == "provider":
        identity = gate.get("execution_identity")
        if isinstance(identity, (list, tuple)) and len(identity) > 1 and identity[0] == "provider":
            return tuple(item for item in identity[1:] if item in QUALITY_PROVIDERS.get(axis, ()))
    if gate.get("execution_mode") == "verified-command":
        providers = gate.get("verification_providers")
        if isinstance(providers, (list, tuple)):
            return tuple(item for item in providers if item in QUALITY_PROVIDERS.get(axis, ()))
    return ()


def _quality_provider_payload(
    gate: Mapping[str, object], check: Mapping[str, object], identity: list[str] | tuple[str, ...]
) -> tuple[object, tuple[str, ...]]:
    """Keep command output distinct from product-owned verifier output."""
    if (
        gate.get("execution_mode") == "provider"
        and len(identity) >= 2
        and identity[0] == "provider"
    ):
        try:
            return json.loads(str(check.get("stdout") or "")), tuple(identity[1:])
        except json.JSONDecodeError:
            return None, ()
    command = check.get("command")
    providers = gate.get("verification_providers")
    if (
        gate.get("execution_mode") == "verified-command"
        and isinstance(command, (list, tuple))
        and tuple(command) == tuple(identity)
        and isinstance(providers, (list, tuple))
    ):
        return check.get("verification"), tuple(providers)
    return None, ()


def _source_contracts(owner: Mapping[str, object]) -> tuple[SourceContract, ...]:
    """Decode serialized source obligations through their original native owner."""
    # A transition plan freezes its policy into read-only mappings, which the model rejects.
    return ProofPolicy.model_validate(
        {"source_contracts": mutable_json(owner.get("source_contracts", ()))}
    ).source_contracts


def source_kinds(owner: Mapping[str, object]) -> dict[str, str]:
    """Derive artifact classification only from valid explicit source obligations."""
    try:
        contracts = _source_contracts(owner)
    except ValidationError:
        return {}
    return {path: contract.kind for contract in contracts for path in contract.members}


def source_verifier_gaps(owner: Mapping[str, object], gates: tuple[Gate, ...]) -> tuple[str, ...]:
    """Reject omitted or command-authored integrity before any native work."""
    try:
        contracts = _source_contracts(owner)
    except ValidationError:
        return ("source_contract_invalid",)
    selected = {gate.id: gate for gate in gates}
    prerequisites = owner.get("source_binding_gaps", ())
    if not isinstance(prerequisites, (list, tuple)) or any(
        not isinstance(gap, str) or not gap for gap in prerequisites
    ):
        return ("source_binding_observation_invalid",)
    gaps: list[str] = list(prerequisites)
    for contract in contracts:
        gate = selected.get(contract.integrity_gate)
        if (
            gate is None
            or not gate.trust_bearing
            or INTEGRITY_PROVIDER not in (*gate.providers, *gate.verification_providers)
        ):
            gaps.append(f"source_integrity_gate_unbound:{contract.integrity_gate}")
    return tuple(dict.fromkeys(gaps))


def source_integrity_gaps(
    policy: Mapping[str, object], checks: object, *, source_tree: str
) -> tuple[str, ...]:
    """Require exact member evidence from each selected product-owned integrity gate."""
    owner = policy.get("owner")
    try:
        contracts = _source_contracts(owner) if isinstance(owner, Mapping) else ()
    except ValidationError:
        return ("source_contract_invalid",)
    if not contracts:
        return ()
    required: dict[str, dict[str, dict[str, str]]] = {}
    for contract in contracts:
        gate_id = contract.integrity_gate
        required.setdefault(gate_id, {}).update(
            {
                path: {"kind": contract.kind, "input_ref": member[0], "member": member[1]}
                for path, member in contract.members.items()
            }
        )
    gates = policy.get("gates", ())
    by_gate = (
        {gate.get("id"): gate for gate in gates if isinstance(gate, Mapping)}
        if isinstance(gates, (list, tuple))
        else {}
    )
    by_check = (
        {check.get("action_id"): check for check in checks if isinstance(check, Mapping)}
        if isinstance(checks, (list, tuple))
        else {}
    )
    expected_members = {
        path: relation for members in required.values() for path, relation in members.items()
    }
    gaps: list[str] = []
    for gate_id, members in required.items():
        gate, check = by_gate.get(gate_id), by_check.get(gate_id)
        report = None
        if isinstance(gate, Mapping) and isinstance(check, Mapping) and execution_succeeded(check):
            identity = gate.get("execution_identity")
            command = check.get("command")
            if (
                isinstance(identity, (list, tuple))
                and isinstance(command, (list, tuple))
                and tuple(command) == tuple(identity)
            ):
                payload, providers = _quality_provider_payload(gate, check, identity)
                observations = (
                    payload.get("providers")
                    if isinstance(payload, Mapping) and payload.get("gate") == gate_id
                    else None
                )
                if INTEGRITY_PROVIDER in providers and isinstance(observations, list):
                    measured = [
                        item.get("report")
                        for item in observations
                        if isinstance(item, Mapping) and item.get("provider") == INTEGRITY_PROVIDER
                    ]
                    if len(measured) == 1:
                        report = measured[0]
        evidence = report.get("source_integrity") if isinstance(report, Mapping) else None
        if (
            not isinstance(report, Mapping)
            or report.get("verdict") != "pass"
            or not source_tree
            or not isinstance(evidence, Mapping)
            or evidence.get("source_tree") != source_tree
            or evidence.get("members") != expected_members
        ):
            gaps.extend(f"source_integrity_unproven:{path}" for path in members)
    return tuple(gaps)
