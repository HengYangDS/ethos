"""Static coupling-layer contracts and scan constants."""

from __future__ import annotations

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
        "validate the ETHOS product repository, without becoming adopter ontology."
    ),
    "profile_or_adapter_binding": (
        "Configured host, provider, projection, distribution, or execution surfaces "
        "that bind evidence without owning product semantics."
    ),
    "default_policy": (
        "Repository-default policies that can be configured without changing semantics."
    ),
    "historical_evidence": "Historical proof records that preserve prior provider facts.",
    "test_fixture": "Tests and fixtures that intentionally model a provider or adopter.",
}
BINDING_UI_PROJECTION_FIELDS = frozenset({"open_action", "open_label", "action", "label"})
ADAPTER_ADMISSION_REQUIRED_FIELDS = frozenset({"authority_ref", "truth_boundary", "decision_state"})
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
            "ethos lane prewrite",
            "ethos lane bind-claim",
            "ethos lane refresh-base",
            "ethos land",
            "ethos land --closeout",
            "ethos lane retire-landed",
            "ethos lane retire-superseded",
            "ethos lane retire-unbound",
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
    "historical_evidence_records": {
        "layer": "historical_evidence",
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
BINDING_METADATA: dict[str, dict[str, object]] = {
    "git_repository_substrate": {
        "required_for": [
            "repository identity",
            "branch roles",
            "HEAD-bound evidence",
            "worktree lifecycle",
        ],
        "replaceability": "hard-bound",
        "degradation_state": "blocked:git_repository_missing",
        "proof_gate": "ethos status --json",
    },
    "branch_role_policy": {
        "required_for": ["semantic role classification", "mutation admission"],
        "replaceability": "hard-bound",
        "degradation_state": "default policy only",
        "proof_gate": "ethos status --json",
    },
    "work_lane_lifecycle_command_contract": {
        "required_for": ["tracked mutation isolation", "local closeout"],
        "replaceability": "hard-bound",
        "degradation_state": "blocked:protected_root_mutation",
        "proof_gate": "ethos prove --full --execute --json",
    },
    "openspec_workspace": {
        "required_for": ["official governance records", "strict specification validation"],
        "replaceability": "mandatory",
        "degradation_state": "blocked:openspec_shape_gap",
        "proof_gate": "openspec validate --all --strict --json",
    },
    "openspec_cli": {
        "required_for": ["official governance validation"],
        "replaceability": "mandatory",
        "degradation_state": "blocked:openspec_cli_unavailable",
        "proof_gate": "openspec validate --all --strict --json",
    },
    "command_json_schema_protocol": {
        "required_for": ["command JSON contracts"],
        "replaceability": "mandatory",
        "degradation_state": "blocked:schema_validation_gap",
        "proof_gate": "ethos quality schemas --json",
    },
    "claims_evidence_digest_protocol": {
        "required_for": ["claim trust envelopes"],
        "replaceability": "mandatory",
        "degradation_state": "blocked:claim_digest_mismatch",
        "proof_gate": "ethos quality claims --json",
    },
    "sqlite_local_state_protocol": {
        "required_for": ["lease and local state coordination"],
        "replaceability": "mandatory",
        "degradation_state": "blocked:state_unavailable",
        "proof_gate": "ethos doctor --json",
    },
    "uv_workspace_toolchain": {
        "required_for": ["product repository proof execution"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "gapped:toolchain_unavailable",
        "proof_gate": "uv run --group dev pytest tests/unit tests/architecture -q",
    },
    "hatchling_build_backend": {
        "required_for": ["Python package build"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "gapped:build_backend_unavailable",
        "proof_gate": "uv build --all-packages",
    },
    "pytest_test_runner": {
        "required_for": ["unit and architecture proof"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "gapped:test_runner_unavailable",
        "proof_gate": "uv run --group dev pytest tests/unit tests/architecture -q",
    },
    "ruff_lint_runner": {
        "required_for": ["lint diagnostics"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "gapped:lint_runner_unavailable",
        "proof_gate": "uv run --group dev ruff check .",
    },
    "gitlab_release_profile": {
        "required_for": ["hosted release profile"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "deferred:remote_publication_adapter_unavailable",
        "proof_gate": "ethos quality release-policy --json",
        "admission": {
            "authority_ref": "docs/governance/product-design-contract.md#binding-taxonomy",
            "truth_boundary": "profile_or_adapter",
            "decision_state": "admitted",
        },
    },
    "mcp_acp_protocol_adapters": {
        "required_for": ["assistant projection adapters"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "deferred:assistant_adapter_unavailable",
        "proof_gate": "ethos assistants doctor --json",
        "admission": {
            "authority_ref": "docs/governance/product-design-contract.md#binding-taxonomy",
            "truth_boundary": "profile_or_adapter",
            "decision_state": "admitted",
        },
    },
    "npm_launcher_distribution_adapter": {
        "required_for": ["npm launcher distribution"],
        "replaceability": "replaceable-adapter",
        "degradation_state": "deferred:npm_distribution_unavailable",
        "proof_gate": "uv build --all-packages",
        "admission": {
            "authority_ref": "docs/governance/product-design-contract.md#binding-taxonomy",
            "truth_boundary": "profile_or_adapter",
            "decision_state": "admitted",
        },
    },
    "historical_evidence_records": {
        "required_for": ["historical auditability"],
        "replaceability": "historical",
        "degradation_state": "nonblocking:historical_evidence_absent",
        "proof_gate": "ethos report --json",
    },
    "provider_test_fixtures": {
        "required_for": ["provider boundary regression tests"],
        "replaceability": "fixture-only",
        "degradation_state": "nonblocking:test_fixture_absent",
        "proof_gate": "uv run --group dev pytest tests/unit tests/architecture -q",
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
GIT_NATIVE_TERMS = ("Git", "git", "worktree", "branch", "refs", "HEAD", "role_policy")
NATIVE_PROTOCOL_FORMATS = (
    "JSON Schema",
    "command JSON",
    "TOML",
    "JSONL",
    "SQLite local state",
)
PRODUCT_REPOSITORY_GATES = ("unit-architecture", "ruff", "build")
