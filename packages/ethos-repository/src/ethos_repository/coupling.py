from __future__ import annotations

import tomllib
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
    "product_toolchain_binding": (
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
BINDING_UI_PROJECTION_FIELDS = frozenset({"open_action", "open_label", "action", "label"})
BRANCH_ROLE_CONFIG_SOURCE = ".ethos/workspace.toml"
BRANCH_ROLE_CONFIG_KEYS = (
    "release_branch",
    "accepted_branch",
    "candidate_branch",
    "work_branch_prefix",
    "submit_branch_prefix",
)
BINDING_CONTRACTS: dict[str, dict[str, object]] = {
    "git_repository_substrate": {
        "layer": "product_semantic_hard_binding",
        "required": True,
        "owns_product_semantics": True,
        "adapter_replaceable": False,
    },
    "branch_role_policy": {
        "layer": "product_semantic_hard_binding",
        "required": True,
        "owns_product_semantics": True,
        "adapter_replaceable": False,
        "config_source": BRANCH_ROLE_CONFIG_SOURCE,
        "config_keys": list(BRANCH_ROLE_CONFIG_KEYS),
    },
    "work_lane_lifecycle_command_contract": {
        "layer": "product_semantic_hard_binding",
        "required": True,
        "owns_product_semantics": True,
        "adapter_replaceable": False,
        "commands": [
            "ethos lane start",
            "ethos lane bind-claim",
            "ethos land",
            "ethos lane retire-landed",
        ],
        "forbidden_workflow_state": ["raw_git_worktree_add"],
    },
    "openspec_workspace": {
        "layer": "mandatory_governance_dependency",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": False,
        "not_product_substrate": True,
    },
    "openspec_cli": {
        "layer": "mandatory_governance_dependency",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": False,
        "not_product_substrate": True,
    },
    "command_json_schema_protocol": {
        "layer": "native_protocol_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": False,
    },
    "claims_evidence_digest_protocol": {
        "layer": "native_protocol_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": False,
    },
    "sqlite_local_state_protocol": {
        "layer": "native_protocol_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": False,
    },
    "uv_workspace_toolchain": {
        "layer": "product_toolchain_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "hatchling_build_backend": {
        "layer": "product_toolchain_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "pytest_test_runner": {
        "layer": "product_toolchain_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "ruff_lint_runner": {
        "layer": "product_toolchain_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "gitlab_release_profile": {
        "layer": "profile_or_adapter_binding",
        "required": True,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "mcp_acp_protocol_adapters": {
        "layer": "profile_or_adapter_binding",
        "required": False,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "npm_launcher_distribution_adapter": {
        "layer": "profile_or_adapter_binding",
        "required": False,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "legacy_evidence_records": {
        "layer": "legacy_evidence",
        "required": False,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
    "provider_test_fixtures": {
        "layer": "test_fixture",
        "required": False,
        "owns_product_semantics": False,
        "adapter_replaceable": True,
    },
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
PRODUCT_HOST_PROJECTION_TERMS = ("Open Worktree", "Checkout")
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


def _host_projection_term_gaps(root: Path) -> list[str]:
    gaps: list[str] = []
    for relative in PRODUCT_SEMANTIC_DOCS:
        path = root / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for term in PRODUCT_HOST_PROJECTION_TERMS:
            if term in text:
                gaps.append(f"product_host_projection_term:{relative}:{term}")
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
        if gate.profile != "product-toolchain":
            gaps.append(f"gate_profile_mismatch:{gate_id}:{gate.profile}")
        if gate.toolchain != "uv-python":
            gaps.append(f"gate_toolchain_mismatch:{gate_id}:{gate.toolchain}")
    return gaps


def _product_toolchain() -> dict[str, object]:
    registry = gate_registry()
    toolchains = sorted({registry[gate_id].toolchain for gate_id in SELF_HOSTING_GATES})
    return {
        "profile": "product-toolchain",
        "layer": "product_toolchain_binding",
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


def _branch_role_policy_metadata(root: Path) -> dict[str, object]:
    path = root / BRANCH_ROLE_CONFIG_SOURCE
    configured = False
    if path.exists():
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            payload = {}
        configured = isinstance(payload.get("branch_roles"), dict)
    return {
        "config_source": BRANCH_ROLE_CONFIG_SOURCE,
        "config_keys": list(BRANCH_ROLE_CONFIG_KEYS),
        "default_policy": not configured,
    }


def _binding_registry(root: Path) -> list[dict[str, object]]:
    policy = load_branch_role_policy(root)
    branch_role_metadata = _branch_role_policy_metadata(root)
    release_profile = _release_host_profile(root)
    product_toolchain = _product_toolchain()
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
            **branch_role_metadata,
            "role_order": [
                str(record["role"]) for record in policy.semantic_order()
            ],
            "configured_patterns": [
                str(record["pattern"]) for record in policy.semantic_order()
            ],
        },
        {
            "id": "work_lane_lifecycle_command_contract",
            "layer": "product_semantic_hard_binding",
            "required": True,
            "owns_product_semantics": True,
            "adapter_replaceable": False,
            "commands": [
                "ethos lane start",
                "ethos lane bind-claim",
                "ethos land",
                "ethos lane retire-landed",
            ],
            "forbidden_workflow_state": ["raw_git_worktree_add"],
        },
        {
            "id": "openspec_workspace",
            "layer": "mandatory_governance_dependency",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "not_a_second_command_plane": True,
            "not_product_substrate": True,
        },
        {
            "id": "openspec_cli",
            "layer": "mandatory_governance_dependency",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "surfaces": [
                "official OpenSpec status",
                "official OpenSpec strict validation",
            ],
            "not_a_second_command_plane": True,
            "not_product_substrate": True,
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
            "id": "claims_evidence_digest_protocol",
            "layer": "native_protocol_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "formats": ["TOML claims", "Markdown evidence", "SHA-256 digest"],
        },
        {
            "id": "sqlite_local_state_protocol",
            "layer": "native_protocol_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": False,
            "formats": ["ignored SQLite local state"],
        },
        {
            "id": "uv_workspace_toolchain",
            "layer": "product_toolchain_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "toolchains": ["uv workspace", "uv lock", "uv run", "uv build"],
            "gates": product_toolchain["gates"],
        },
        {
            "id": "hatchling_build_backend",
            "layer": "product_toolchain_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "surfaces": ["PEP 517 build backend", "wheel", "sdist"],
        },
        {
            "id": "pytest_test_runner",
            "layer": "product_toolchain_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "gates": ["unit-architecture"],
            "surfaces": ["pytest"],
        },
        {
            "id": "ruff_lint_runner",
            "layer": "product_toolchain_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "gates": ["ruff"],
            "surfaces": ["Ruff"],
        },
        {
            "id": "gitlab_release_profile",
            "layer": "profile_or_adapter_binding",
            "required": True,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "provider": release_profile.get("provider", ""),
            "surfaces": release_profile.get("surfaces", {}),
        },
        {
            "id": "mcp_acp_protocol_adapters",
            "layer": "profile_or_adapter_binding",
            "required": False,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "surfaces": ["MCP", "ACP", "assistant context projections"],
        },
        {
            "id": "npm_launcher_distribution_adapter",
            "layer": "profile_or_adapter_binding",
            "required": False,
            "owns_product_semantics": False,
            "adapter_replaceable": True,
            "surfaces": ["distributions/npm", "npm launcher"],
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


def _binding_registry_gaps(entries: list[dict[str, object]]) -> list[str]:
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
        if layer not in COUPLING_LAYERS:
            gaps.append(f"binding_registry_unknown_layer:{entry_id}:{layer}")
        for field in sorted(BINDING_UI_PROJECTION_FIELDS & set(entry)):
            gaps.append(f"binding_registry_ui_projection:{entry_id}:{field}")

    for entry_id, expected in BINDING_CONTRACTS.items():
        entry = entry_by_id.get(entry_id)
        if entry is None:
            gaps.append(f"binding_registry_missing:{entry_id}")
            continue
        for key in ("layer", "required", "owns_product_semantics", "adapter_replaceable"):
            if entry.get(key) != expected[key]:
                gaps.append(f"binding_registry_{key}:{entry_id}:{entry.get(key)}")
                if key == "owns_product_semantics" and expected[key] is False:
                    gaps.append(f"binding_registry_product_semantics:{entry_id}")
        for key, expected_value in expected.items():
            if key in {
                "layer",
                "required",
                "owns_product_semantics",
                "adapter_replaceable",
                "not_product_substrate",
            }:
                continue
            if entry.get(key) != expected_value:
                gaps.append(f"binding_registry_{key}:{entry_id}:{entry.get(key)}")
        if expected.get("not_product_substrate") and entry.get("not_product_substrate") is not True:
            gaps.append(f"binding_registry_product_substrate:{entry_id}")
        if (
            entry.get("layer") != "product_semantic_hard_binding"
            and entry.get("owns_product_semantics") is True
        ):
            gap = f"binding_registry_product_semantics:{entry_id}"
            if gap not in gaps:
                gaps.append(gap)
    return gaps


def coupling_audit_report(root: Path) -> dict[str, Any]:
    release = _release_report(root)
    registry = _binding_registry(root)
    gaps = (
        _vendor_term_gaps(root)
        + _host_projection_term_gaps(root)
        + _gate_profile_gaps()
        + _binding_registry_gaps(registry)
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
        "openspec_governance": _openspec_governance(),
        "native_protocols": _native_protocols(),
        "binding_registry": registry,
        "release_product_files": list(release["required_files"]),
        "release_host_profile": _release_host_profile(root),
        "product_toolchain": _product_toolchain(),
        "scanned_product_docs": [
            relative for relative in PRODUCT_SEMANTIC_DOCS if (root / relative).exists()
        ],
    }
