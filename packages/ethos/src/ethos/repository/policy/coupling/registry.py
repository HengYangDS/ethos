"""Binding-registry construction and validation."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.repository.policy.coupling.contracts import ADAPTER_ADMISSION_REQUIRED_FIELDS
from ethos.repository.policy.coupling.contracts import BINDING_CONTRACTS
from ethos.repository.policy.coupling.contracts import BINDING_METADATA
from ethos.repository.policy.coupling.contracts import BINDING_UI_PROJECTION_FIELDS
from ethos.repository.policy.coupling.contracts import BRANCH_ROLE_CONFIG_KEYS
from ethos.repository.policy.coupling.contracts import BRANCH_ROLE_CONFIG_SOURCE
from ethos.repository.policy.coupling.contracts import COUPLING_LAYERS
from ethos.repository.policy.coupling.release import release_host_profile
from ethos.repository.policy.coupling.toolchain import product_toolchain
from ethos_core.contracts.branch.roles import load_branch_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def branch_role_policy_metadata(root: Path) -> dict[str, object]:
    """Return branch-role policy source metadata for coupling reports."""
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


def binding_registry(root: Path) -> list[dict[str, object]]:
    """Build the coupling binding registry for a repository root."""
    policy = load_branch_role_policy(root)
    branch_role_metadata = branch_role_policy_metadata(root)
    release_profile = release_host_profile(root)
    toolchain = product_toolchain()
    runtime_fields: list[dict[str, object]] = [
        {
            "id": "git_repository_substrate",
            "surfaces": ["commits", "refs", "branches", "worktrees", "HEAD"],
        },
        {
            "id": "branch_role_policy",
            **branch_role_metadata,
            "role_order": [str(record["role"]) for record in policy.semantic_order()],
            "configured_patterns": [str(record["pattern"]) for record in policy.semantic_order()],
        },
        {
            "id": "work_lane_lifecycle_command_contract",
            "commands": [
                "ethos lane start",
                "ethos lane prewrite",
                "ethos lane bind-claim",
                "ethos lane refresh-base",
                "ethos land",
                "ethos land --closeout",
                "ethos lane retire landed",
                "ethos lane retire superseded",
                "ethos lane retire unbound",
            ],
            "forbidden_workflow_state": ["raw_git_worktree_add"],
        },
        {
            "id": "openspec_workspace",
            "not_a_second_command_plane": True,
            "not_product_substrate": True,
        },
        {
            "id": "openspec_cli",
            "surfaces": [
                "official OpenSpec status",
                "official OpenSpec strict validation",
            ],
            "not_a_second_command_plane": True,
            "not_product_substrate": True,
        },
        {
            "id": "command_json_schema_protocol",
            "formats": ["command JSON", "JSON Schema"],
        },
        {
            "id": "claims_evidence_digest_protocol",
            "formats": ["TOML claims", "Markdown evidence", "SHA-256 digest"],
        },
        {
            "id": "sqlite_local_state_protocol",
            "formats": ["ignored SQLite local state"],
        },
        {
            "id": "uv_workspace_toolchain",
            "toolchains": ["uv workspace", "uv lock", "uv run", "uv build"],
            "gates": toolchain["gates"],
        },
        {
            "id": "hatchling_build_backend",
            "surfaces": ["PEP 517 build backend", "wheel", "sdist"],
        },
        {
            "id": "pytest_test_runner",
            "gates": ["unit-architecture"],
            "surfaces": ["pytest"],
        },
        {
            "id": "ruff_lint_runner",
            "gates": ["ruff"],
            "surfaces": ["Ruff"],
        },
        {
            "id": "gitlab_release_profile",
            "provider": release_profile.get("provider", ""),
            "surfaces": release_profile.get("surfaces", {}),
        },
        {
            "id": "mcp_acp_protocol_adapters",
            "surfaces": ["MCP", "ACP", "assistant context projections"],
        },
        {
            "id": "npm_launcher_distribution_adapter",
            "surfaces": ["distributions/npm", "npm launcher"],
        },
        {
            "id": "historical_evidence_records",
            "surfaces": ["archived evidence", "migration oracle records"],
        },
        {
            "id": "provider_test_fixtures",
            "surfaces": ["hosted provider fixtures", "adopter fixtures"],
        },
    ]
    return [
        {
            **BINDING_CONTRACTS[str(entry["id"])],
            **entry,
            **BINDING_METADATA[str(entry["id"])],
        }
        for entry in runtime_fields
    ]


def binding_taxonomy_gaps(
    entry_id: str,
    entry: dict[str, object],
    expected: dict[str, object],
) -> list[str]:
    """Enforce layering taxonomy invariants for a single binding entry."""
    gaps: list[str] = []
    if entry.get("layer") != expected["layer"]:
        gaps.append(f"binding_registry_layer:{entry_id}:{entry.get('layer')}")
    if expected["owns_product_semantics"] is False and entry.get("owns_product_semantics") is True:
        gaps.append(f"binding_registry_product_semantics:{entry_id}")
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


def adapter_admission_gaps(entry_id: str, entry: dict[str, object]) -> list[str]:
    """Return adapter admission gaps for one registry entry."""
    if entry.get("layer") != "profile_or_adapter_binding":
        return []
    admission = entry.get("admission")
    if not isinstance(admission, dict):
        return [f"binding_registry_adapter_admission_missing:{entry_id}"]
    gaps = []
    for field in sorted(ADAPTER_ADMISSION_REQUIRED_FIELDS):
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


def binding_registry_gaps(entries: list[dict[str, object]]) -> list[str]:
    """Return binding-registry shape and taxonomy gaps."""
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
        gaps.extend(adapter_admission_gaps(entry_id, entry))

    for entry_id, expected in BINDING_CONTRACTS.items():
        entry = entry_by_id.get(entry_id)
        if entry is None:
            gaps.append(f"binding_registry_missing:{entry_id}")
            continue
        gaps.extend(binding_taxonomy_gaps(entry_id, entry, expected))
    return gaps
