"""Coupling audit report composition."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.coupling.contracts import COUPLING_LAYERS
from ethos.repository.policy.coupling.contracts import GIT_NATIVE_TERMS
from ethos.repository.policy.coupling.contracts import NATIVE_PROTOCOL_FORMATS
from ethos.repository.policy.coupling.contracts import PRODUCT_SEMANTIC_DOCS
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


def openspec_governance() -> dict[str, object]:
    """Return the OpenSpec governance binding descriptor."""
    return {
        "required": True,
        "layer": "mandatory_governance_dependency",
        "capability": "official-native governance records",
        "execution_surface": "profile_or_adapter_binding",
        "not_a_second_command_plane": True,
    }


def native_protocols() -> dict[str, object]:
    """Return native protocol binding descriptors."""
    return {
        "layer": "native_protocol_binding",
        "formats": list(NATIVE_PROTOCOL_FORMATS),
        "provider_optional": False,
    }


def coupling_audit_report(root: Path) -> dict[str, Any]:
    """Return the product/profile/toolchain coupling audit report."""
    release = release_report(root)
    registry = binding_registry(root)
    gaps = (
        vendor_term_gaps(root)
        + host_projection_term_gaps(root)
        + gate_profile_gaps()
        + binding_registry_gaps(registry)
    )
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "taxonomy": dict(COUPLING_LAYERS),
        "git_native": {
            "strongly_bound": True,
            "layer": "product_semantic_hard_binding",
            "allowed_terms": list(GIT_NATIVE_TERMS),
            "not_a_generic_vcs_abstraction": True,
        },
        "openspec_governance": openspec_governance(),
        "native_protocols": native_protocols(),
        "binding_registry": registry,
        "release_product_files": list(release["required_files"]),
        "release_host_profile": release_host_profile(root),
        "product_toolchain": product_toolchain(),
        "scanned_product_docs": [
            relative for relative in PRODUCT_SEMANTIC_DOCS if (root / relative).exists()
        ],
    }
