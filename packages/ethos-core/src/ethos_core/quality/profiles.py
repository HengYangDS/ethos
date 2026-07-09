from __future__ import annotations

from ethos_core.quality.models import QualityAssetClass
from ethos_core.quality.models import ToolAdapterProfile

ASSET_CLASSES = (
    QualityAssetClass(
        class_name="python-code",
        role="runtime source and tests",
        dimensions=(
            "format",
            "lint",
            "type",
            "test",
            "complexity",
            "determinism",
            "dependency-hygiene",
        ),
        default_adapters=(
            "ruff",
            "pytest",
            "ty",
            "deptry",
            "ethos-docstrings-google",
            "ethos-module-layout",
        ),
    ),
    QualityAssetClass(
        class_name="markdown-docs",
        role="reader-facing repository knowledge",
        dimensions=("format", "links", "anchors", "front-matter", "command-examples", "spelling"),
        default_adapters=("markdown-it", "lychee", "codespell", "ethos-command-registry"),
    ),
    QualityAssetClass(
        class_name="shell-scripts",
        role="local operational commands",
        dimensions=("format", "lint", "portability"),
        default_adapters=("shfmt", "shellcheck"),
    ),
    QualityAssetClass(
        class_name="toml-config",
        role="human-authored repository configuration",
        dimensions=("format", "schema", "determinism"),
        default_adapters=("taplo", "check-jsonschema"),
    ),
    QualityAssetClass(
        class_name="json-contracts",
        role="machine contracts and output schemas",
        dimensions=("format", "schema", "stable-ordering"),
        default_adapters=("jsonschema", "jq"),
    ),
    QualityAssetClass(
        class_name="yaml-config",
        role="host and workflow projections",
        dimensions=("format", "schema", "projection-boundary"),
        default_adapters=("yamllint", "check-jsonschema"),
    ),
    QualityAssetClass(
        class_name="evidence",
        role="durable proof and claim support",
        dimensions=("freshness", "digest", "provenance", "head-binding"),
        default_adapters=("ethos-claims", "in-toto"),
    ),
    QualityAssetClass(
        class_name="release-artifacts",
        role="build and publication readiness outputs",
        dimensions=("provenance", "sbom", "attestation", "reproducibility"),
        default_adapters=("uv-build", "spdx", "slsa"),
    ),
    QualityAssetClass(
        class_name="adopter-profile",
        role="repository-specific governance mapping",
        dimensions=("boundary", "schema", "projection", "parity"),
        default_adapters=("ethos-profile",),
    ),
)

TOOL_ADAPTERS = (
    ToolAdapterProfile(
        id="ruff",
        standard="Ruff Python lint and format",
        asset_classes=("python-code",),
        dimensions=("format", "lint"),
        boundary="adapter-executes-tool-quality-owns-verdict",
    ),
    ToolAdapterProfile(
        id="ethos-docstrings-google",
        standard="ETHOS public-surface Google docstring coverage and style",
        asset_classes=("python-code",),
        dimensions=("documentation", "intent"),
        boundary="inprocess-policy-checks-public-surface-intent",
    ),
    ToolAdapterProfile(
        id="ethos-module-layout",
        standard="ETHOS semantic subpackage and module-layout policy",
        asset_classes=("python-code",),
        dimensions=("module-layout", "semantic-subpackages", "import-discipline"),
        boundary="inprocess-policy-checks-layout-no-compatibility-facades",
    ),
    ToolAdapterProfile(
        id="pytest",
        standard="pytest",
        asset_classes=("python-code",),
        dimensions=("test",),
        boundary="adapter-executes-tests-quality-classifies-evidence",
    ),
    ToolAdapterProfile(
        id="ty",
        standard="Python type checking",
        asset_classes=("python-code",),
        dimensions=("type",),
        boundary="optional-type-adapter",
    ),
    ToolAdapterProfile(
        id="lychee",
        standard="link checking",
        asset_classes=("markdown-docs",),
        dimensions=("links",),
        boundary="adapter-checks-links-docs-profile-owns-requirement",
    ),
    ToolAdapterProfile(
        id="markdown-it",
        standard="CommonMark-compatible parsing",
        asset_classes=("markdown-docs",),
        dimensions=("anchors", "structure"),
        boundary="parser-adapter-not-doc-truth",
    ),
    ToolAdapterProfile(
        id="shellcheck",
        standard="ShellCheck",
        asset_classes=("shell-scripts",),
        dimensions=("lint",),
        boundary="shell-quality-adapter",
    ),
    ToolAdapterProfile(
        id="shfmt",
        standard="shfmt",
        asset_classes=("shell-scripts",),
        dimensions=("format",),
        boundary="shell-format-adapter",
    ),
    ToolAdapterProfile(
        id="taplo",
        standard="Taplo TOML",
        asset_classes=("toml-config",),
        dimensions=("format", "schema"),
        boundary="toml-quality-adapter",
    ),
    ToolAdapterProfile(
        id="jsonschema",
        standard="JSON Schema draft 2020-12",
        asset_classes=("json-contracts",),
        dimensions=("schema",),
        boundary="contract-validation-adapter",
    ),
    ToolAdapterProfile(
        id="yamllint",
        standard="YAML linting",
        asset_classes=("yaml-config",),
        dimensions=("format", "lint"),
        boundary="yaml-quality-adapter",
    ),
    ToolAdapterProfile(
        id="deptry",
        standard="Python dependency hygiene",
        asset_classes=("python-code",),
        dimensions=("dependency-hygiene",),
        boundary="package-local-metadata-check-not-vulnerability-audit",
    ),
    ToolAdapterProfile(
        id="codespell",
        standard="spelling lint",
        asset_classes=("markdown-docs",),
        dimensions=("spelling",),
        boundary="report-first-prose-check-no-rewrite-no-evidence-truth",
    ),
    ToolAdapterProfile(
        id="check-jsonschema",
        standard="JSON Schema metaschema validation",
        asset_classes=("json-contracts", "toml-config", "yaml-config"),
        dimensions=("schema",),
        boundary="schema-document-hygiene-not-command-payload-proof",
    ),
    ToolAdapterProfile(
        id="hosted-provider-observation",
        standard="GitHub/GitLab hosted observation envelope",
        asset_classes=("yaml-config", "evidence"),
        dimensions=("provider-observation",),
        boundary="observation-only-not-repository-proof-or-hosted-success-claim",
    ),
    ToolAdapterProfile(
        id="nox",
        standard="Nox Python session runner",
        asset_classes=("adopter-profile",),
        dimensions=("session-runner",),
        boundary="adapter-only-adopter-owned-command-plane-not-ethos-core",
    ),
    ToolAdapterProfile(
        id="pixi",
        standard="Pixi environment manager",
        asset_classes=("adopter-profile",),
        dimensions=("environment-runner",),
        boundary="adapter-only-environment-profile-not-ethos-runtime-substrate",
    ),
    ToolAdapterProfile(
        id="pants",
        standard="Pants graph build system",
        asset_classes=("adopter-profile",),
        dimensions=("graph-changed-scope",),
        boundary="adapter-only-graph-signal-not-ethos-kernel",
    ),
    ToolAdapterProfile(
        id="task-ledger",
        standard="Task ledger or backlog intake adapter",
        asset_classes=("adopter-profile",),
        dimensions=("intake", "task-projection"),
        boundary="adapter-only-task-ui-not-change-claim-lifecycle-owner",
    ),
    ToolAdapterProfile(
        id="agent-method-pack",
        standard="Agent method pack discipline",
        asset_classes=("adopter-profile",),
        dimensions=("agent-discipline", "review", "verification"),
        boundary="optional-method-pack-not-proof-substitute-or-runtime-dependency",
    ),
)


def product_quality_profile() -> dict[str, object]:
    return {
        "schema_version": 1,
        "asset_classes": [asset.to_dict() for asset in ASSET_CLASSES],
        "tool_adapters": [adapter.to_dict() for adapter in TOOL_ADAPTERS],
        "format_governance": {
            "human_config": ["toml-config"],
            "machine_contract": ["json-contracts"],
            "host_projection": ["yaml-config"],
            "append_only": ["evidence"],
        },
    }


def tool_profiles() -> dict[str, object]:
    return {
        "schema_version": 1,
        "tool_adapters": [adapter.to_dict() for adapter in TOOL_ADAPTERS],
    }
