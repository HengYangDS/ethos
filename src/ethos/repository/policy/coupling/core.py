"""Coupling audit report composition."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.registry.declarations import CouplingDeclaration
from ethos.contracts.registry.declarations import load_coupling_declaration
from ethos.repository.policy.coupling.documents import host_projection_term_gaps
from ethos.repository.policy.coupling.documents import vendor_term_gaps
from ethos.repository.policy.coupling.registry import binding_registry
from ethos.repository.policy.coupling.registry import binding_registry_gaps
from ethos.repository.policy.coupling.release import release_host_profile
from ethos.repository.policy.coupling.release import release_report
from ethos.repository.policy.coupling.toolchain import gate_profile_gaps
from ethos.repository.policy.coupling.toolchain import product_toolchain

if TYPE_CHECKING:
    from pathlib import Path


def openspec_governance(declaration: CouplingDeclaration) -> dict[str, object]:
    """Return the declared OpenSpec governance binding descriptor."""
    return declaration.openspec_governance.model_dump(mode="json")


def native_protocols(declaration: CouplingDeclaration) -> dict[str, object]:
    """Return the declared native protocol binding descriptors."""
    return declaration.native_protocols.model_dump(mode="json")


def coupling_audit_report(root: Path) -> dict[str, Any]:
    """Return the product/profile/toolchain coupling audit report."""
    declaration = load_coupling_declaration()
    release = release_report(root)
    registry = binding_registry(root)
    gaps = (
        vendor_term_gaps(root)
        + host_projection_term_gaps(root)
        + gate_profile_gaps()
        + binding_registry_gaps(registry, declaration)
    )
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "taxonomy": dict(declaration.layers),
        "git_native": {
            "strongly_bound": True,
            "layer": "product_semantic_hard_binding",
            "allowed_terms": list(declaration.git_native_terms),
            "not_a_generic_vcs_abstraction": True,
        },
        "openspec_governance": openspec_governance(declaration),
        "native_protocols": native_protocols(declaration),
        "binding_registry": registry,
        "release_product_files": list(release["required_files"]),
        "release_host_profile": release_host_profile(root),
        "product_toolchain": product_toolchain(),
        "scanned_product_docs": [
            relative for relative in declaration.product_semantic_docs if (root / relative).exists()
        ],
    }
