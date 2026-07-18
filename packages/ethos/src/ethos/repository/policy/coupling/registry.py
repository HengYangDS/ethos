"""Binding-registry projection and validation."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.repository.policy.coupling.release import release_host_profile
from ethos.repository.policy.coupling.toolchain import product_toolchain
from ethos_core.contracts.branch.roles import load_branch_role_policy
from ethos_core.contracts.registry.declarations import CouplingBinding
from ethos_core.contracts.registry.declarations import CouplingDeclaration
from ethos_core.contracts.registry.declarations import load_coupling_declaration

if TYPE_CHECKING:
    from pathlib import Path


def branch_role_policy_metadata(root: Path) -> dict[str, object]:
    """Return declared branch-role policy source metadata for coupling reports."""
    binding = load_coupling_declaration().binding("branch_role_policy")
    path = root / str(binding.config_source)
    configured = False
    if path.exists():
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            payload = {}
        configured = isinstance(payload.get("branch_roles"), dict)
    return {
        "config_source": binding.config_source,
        "config_keys": list(binding.config_keys),
        "default_policy": not configured,
    }


def binding_registry(root: Path) -> list[dict[str, object]]:
    """Compile declared bindings and overlay only live adapter facts."""
    declaration = load_coupling_declaration()
    policy = load_branch_role_policy(root)
    runtime = {
        "branch_role_policy": {
            **branch_role_policy_metadata(root),
            "role_order": [str(record["role"]) for record in policy.semantic_order()],
            "configured_patterns": [str(record["pattern"]) for record in policy.semantic_order()],
        },
        "uv_workspace_toolchain": {"gates": product_toolchain()["gates"]},
        "gitlab_release_profile": {
            "provider": release_host_profile(root).get("provider", ""),
            "surfaces": release_host_profile(root).get("surfaces", {}),
        },
    }
    return [
        {**binding.projection(), **runtime.get(binding.id, {})} for binding in declaration.bindings
    ]


def binding_taxonomy_gaps(
    entry_id: str,
    entry: dict[str, object],
    expected: CouplingBinding,
) -> list[str]:
    """Enforce declared layering taxonomy invariants for one binding entry."""
    gaps: list[str] = []
    if entry.get("layer") != expected.layer:
        gaps.append(f"binding_registry_layer:{entry_id}:{entry.get('layer')}")
    if not expected.owns_product_semantics and entry.get("owns_product_semantics") is True:
        gaps.append(f"binding_registry_product_semantics:{entry_id}")
    if expected.not_product_substrate and entry.get("not_product_substrate") is not True:
        gaps.append(f"binding_registry_product_substrate:{entry_id}")
    if (
        entry.get("layer") != "product_semantic_hard_binding"
        and entry.get("owns_product_semantics") is True
    ):
        gap = f"binding_registry_product_semantics:{entry_id}"
        if gap not in gaps:
            gaps.append(gap)
    return gaps


def adapter_admission_gaps(entry_id: str, entry: dict[str, object]) -> list[str]:
    """Return adapter admission gaps for one registry entry."""
    if entry.get("layer") != "profile_or_adapter_binding":
        return []
    admission = entry.get("admission")
    if not isinstance(admission, dict):
        return [f"binding_registry_adapter_admission_missing:{entry_id}"]
    gaps = []
    for field in ("authority_ref", "decision_state", "truth_boundary"):
        if not admission.get(field):
            gaps.append(f"binding_registry_adapter_admission_field:{entry_id}:{field}")
    if admission.get("truth_boundary") != "profile_or_adapter":
        gaps.append(
            f"binding_registry_adapter_truth_boundary:{entry_id}:{admission.get('truth_boundary')}"
        )
    if admission.get("decision_state") != "admitted":
        gaps.append(
            f"binding_registry_adapter_decision_state:{entry_id}:{admission.get('decision_state')}"
        )
    return gaps


def binding_registry_gaps(
    entries: list[dict[str, object]], declaration: CouplingDeclaration | None = None
) -> list[str]:
    """Return binding-registry shape and taxonomy gaps."""
    contract = declaration or load_coupling_declaration()
    gaps: list[str] = []
    entry_by_id: dict[str, dict[str, object]] = {}
    for entry in entries:
        entry_id = str(entry.get("id", ""))
        if not entry_id:
            gaps.append("binding_registry_missing_id")
            continue
        if entry_id in entry_by_id:
            gaps.append(f"binding_registry_duplicate:{entry_id}")
        entry_by_id[entry_id] = entry
        layer = str(entry.get("layer", ""))
        if layer not in contract.layers:
            gaps.append(f"binding_registry_unknown_layer:{entry_id}:{layer}")
        for field in sorted(set(contract.ui_projection_fields) & set(entry)):
            gaps.append(f"binding_registry_ui_projection:{entry_id}:{field}")
        gaps.extend(adapter_admission_gaps(entry_id, entry))

    for expected in contract.bindings:
        entry = entry_by_id.get(expected.id)
        if entry is None:
            gaps.append(f"binding_registry_missing:{expected.id}")
            continue
        gaps.extend(binding_taxonomy_gaps(expected.id, entry, expected))
    return gaps
