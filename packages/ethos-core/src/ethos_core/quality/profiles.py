from __future__ import annotations

import tomllib
from pathlib import Path

from ethos_core.quality.models import QualityAssetClass

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
            "vulnerability",
        ),
        default_adapters=(
            "ruff",
            "pytest",
            "ty",
            "deptry",
            "pip-audit",
            "ethos-docstrings-google",
            "ethos-module-layout",
        ),
    ),
    QualityAssetClass(
        class_name="markdown-docs",
        role="reader-facing repository knowledge",
        dimensions=(
            "format",
            "links",
            "anchors",
            "front-matter",
            "command-examples",
            "spelling",
        ),
        default_adapters=(
            "markdown-it",
            "lychee",
            "codespell",
            "ethos-command-registry",
        ),
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


def product_quality_profile(root: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "asset_classes": [asset.to_dict() for asset in ASSET_CLASSES],
        **tool_profiles(root),
        "format_governance": {
            "human_config": ["toml-config"],
            "machine_contract": ["json-contracts"],
            "host_projection": ["yaml-config"],
            "append_only": ["evidence"],
        },
    }


def tool_profiles(root: Path) -> dict[str, object]:
    catalog_path = root / "system" / "tools.toml"
    if not catalog_path.is_file():
        catalog_path = next(
            parent / "system" / "tools.toml"
            for parent in Path(__file__).resolve().parents
            if (parent / "system" / "tools.toml").is_file()
        )
    catalog = tomllib.loads(catalog_path.read_text(encoding="utf-8"))
    entries = catalog.get("tool", [])
    if not isinstance(entries, list):
        raise TypeError("system/tools.toml must declare a tool array")
    return {
        "schema_version": 1,
        "tool_adapters": [
            {"id": entry["concern"], "standard": entry["tool"], **entry}
            for entry in entries
            if isinstance(entry, dict)
        ],
    }
