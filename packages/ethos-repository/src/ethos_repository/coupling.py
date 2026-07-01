from __future__ import annotations

from pathlib import Path
from typing import Any

from ethos_contracts.branch_roles import load_branch_role_policy

from ethos_repository.gates import gate_registry
from ethos_repository.release import REQUIRED_RELEASE_FILES, release_policy_report

COUPLING_LAYERS: dict[str, str] = {
    "product_semantic_hard_binding": (
        "Kernel chain, public command semantics, Git facts, branch roles, and "
        "worktree lifecycle that define ETHOS product behavior."
    ),
    "mandatory_governance_dependency": (
        "Official governance capabilities required for current planning records, "
        "deep proof, release proof, or archive proof."
    ),
    "native_protocol_binding": (
        "Repository-local data protocols that keep command, config, state, event, "
        "and schema contracts stable across adapters."
    ),
    "self_hosting_toolchain_binding": (
        "Current product-repository implementation and proof tools required to "
        "validate ETHOS itself, without becoming adopter ontology."
    ),
    "profile_or_adapter_binding": (
        "Configured host, provider, projection, distribution, or execution surfaces "
        "that bind evidence without owning product semantics."
    ),
    "default_policy": (
        "Repository-default policies that can be configured without changing semantics."
    ),
    "legacy_evidence": "Historical proof records that preserve prior provider facts.",
    "test_fixture": "Tests and fixtures that intentionally model a provider or adopter.",
}

PRODUCT_SEMANTIC_DOCS = (
    "docs/governance/product-design-contract.md",
    "docs/reference/command-plane.md",
    "docs/architecture/runner-and-mutation.md",
    "docs/architecture/package-ontology.md",
    "docs/governance/release-governance.md",
    "docs/architecture/gate-runner.md",
)
PRODUCT_VENDOR_TERMS = (
    "PyCharm",
    "Claude",
    "Codex",
    "OpenAI",
    "GPT",
    "IDE",
    "JetBrains",
    "Anthropic",
    "Gemini",
    "Copilot",
    "Cursor",
    "Windsurf",
)
GIT_NATIVE_TERMS = ("Git", "git", "worktree", "branch", "candidate/dev", "work/*", "submit/*")
NATIVE_PROTOCOL_FORMATS = (
    "JSON Schema",
    "command JSON",
    "TOML",
    "JSONL",
    "SQLite local state",
)
SELF_HOSTING_GATES = ("unit-architecture", "ruff", "build")


def _vendor_term_gaps(root: Path) -> list[str]:
    gaps: list[str] = []
    for relative in PRODUCT_SEMANTIC_DOCS:
        path = root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for term in PRODUCT_VENDOR_TERMS:
            if term in text:
                gaps.append(f"product_vendor_term:{relative}:{term}")
    return gaps


def _release_report(root: Path) -> dict[str, Any]:
    if not (root / "pyproject.toml").exists():
        return {
            "required_files": list(REQUIRED_RELEASE_FILES),
            "host_profile": {
                "provider": "",
                "layer": "profile_or_adapter_binding",
                "surfaces": {},
            },
            "required_gaps": [],
        }
    return release_policy_report(root)


def _gate_profile_gaps() -> list[str]:
    registry = gate_registry()
    gaps = []
    for gate_id in SELF_HOSTING_GATES:
        gate = registry[gate_id]
        if gate.profile != "self-hosting":
            gaps.append(f"gate_profile_mismatch:{gate_id}:{gate.profile}")
        if gate.toolchain != "uv-python":
            gaps.append(f"gate_toolchain_mismatch:{gate_id}:{gate.toolchain}")
    return gaps


def _self_hosting_toolchain() -> dict[str, object]:
    registry = gate_registry()
    toolchains = sorted({registry[gate_id].toolchain for gate_id in SELF_HOSTING_GATES})
    return {
        "profile": "self-hosting",
        "layer": "self_hosting_toolchain_binding",
        "gates": list(SELF_HOSTING_GATES),
        "toolchains": toolchains,
        "product_ontology_anchor": False,
    }


def _release_host_profile(root: Path) -> dict[str, object]:
    profile = dict(_release_report(root)["host_profile"])
    profile["layer"] = "profile_or_adapter_binding"
    return profile


def _openspec_governance() -> dict[str, object]:
    return {
        "required": True,
        "layer": "mandatory_governance_dependency",
        "capability": "official-native governance records",
        "execution_surface": "profile_or_adapter_binding",
        "not_a_second_command_plane": True,
    }


def _native_protocols() -> dict[str, object]:
    return {
        "layer": "native_protocol_binding",
        "formats": list(NATIVE_PROTOCOL_FORMATS),
        "provider_optional": False,
    }


def _binding_registry(root: Path) -> list[dict[str, object]]:
    policy = load_branch_role_policy(root)
    release_profile = _release_host_profile(root)
    return [
        {
            "id": "git_repository_substrate",
            "layer": "product_semantic_hard_binding",
            "required": True,
            "owns_product_semantics": True,
            "adapter_replaceable": False,
            "surfaces": ["commits", "refs", "branches", "worktrees", "HEAD"],
        },
        {
            "id": "branch_role_policy",
            "layer": "product_semantic_hard_binding",
            "required": True,
            "owns_product_semantics": True,
            "adapter_replaceable": False,
            "role_order": [
                str(record["role"]) for record in policy.semantic_order()
            ],
            "configured_patterns": [
                str(record["pattern"]) for record in policy.semantic_order()
            ],
        },
        {
            "id": "openspec_workspace",
            "layer": "mandatory_governance_dependency",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "not_a_second_command_plane": True,
        },
        {
            "id": "command_json_schema_protocol",
            "layer": "native_protocol_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "formats": ["command JSON", "JSON Schema"],
        },
        {
            "id": "claims_evidence_protocol",
            "layer": "native_protocol_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "formats": ["TOML", "Markdown evidence", "SHA-256 digest"],
        },
        {
            "id": "local_state_protocol",
            "layer": "native_protocol_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "formats": ["ignored SQLite local state"],
        },
        {
            "id": "self_hosting_python_toolchain",
            "layer": "self_hosting_toolchain_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "toolchains": _self_hosting_toolchain()["toolchains"],
            "gates": _self_hosting_toolchain()["gates"],
        },
        {
            "id": "release_host_profile",
            "layer": "profile_or_adapter_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "provider": release_profile.get("provider", ""),
            "surfaces": release_profile.get("surfaces", {}),
        },
        {
            "id": "assistant_protocol_adapters",
            "layer": "profile_or_adapter_binding",
            "required": False,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "surfaces": ["MCP", "ACP", "assistant context projections"],
        },
        {
            "id": "legacy_evidence_records",
            "layer": "legacy_evidence",
            "required": False,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "surfaces": ["archived evidence", "migration oracle records"],
        },
        {
            "id": "provider_test_fixtures",
            "layer": "test_fixture",
            "required": False,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "surfaces": ["hosted provider fixtures", "adopter fixtures"],
        },
    ]


def coupling_audit_report(root: Path) -> dict[str, Any]:
    release = _release_report(root)
    gaps = _vendor_term_gaps(root) + _gate_profile_gaps()
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
        "openspec_governance": _openspec_governance(),
        "native_protocols": _native_protocols(),
        "binding_registry": _binding_registry(root),
        "release_product_files": list(release["required_files"]),
        "release_host_profile": _release_host_profile(root),
        "self_hosting_toolchain": _self_hosting_toolchain(),
        "scanned_product_docs": [
            relative for relative in PRODUCT_SEMANTIC_DOCS if (root / relative).exists()
        ],
    }
