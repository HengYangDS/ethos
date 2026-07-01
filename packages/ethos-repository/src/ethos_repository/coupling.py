from __future__ import annotations

from pathlib import Path
from typing import Any

from ethos_repository.gates import gate_registry
from ethos_repository.release import REQUIRED_RELEASE_FILES, release_policy_report

COUPLING_LAYERS: dict[str, str] = {
    "product_semantic": (
        "Git-native ETHOS contracts, command JSON, branch roles, and worktree lifecycle."
    ),
    "default_policy": (
        "Repository-default policies that can be configured without changing semantics."
    ),
    "profile_config": "Adopter or host-provider configuration such as hosted CI surfaces.",
    "adapter_projection": "Generated or committed files consumed by external hosts.",
    "self_hosting_evidence": "Current product-repository toolchain used to prove ETHOS itself.",
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
PRODUCT_VENDOR_TERMS = ("PyCharm", "Claude", "Codex", "OpenAI", "GPT", "IDE")
GIT_NATIVE_TERMS = ("Git", "git", "worktree", "branch", "candidate/dev", "work/*", "submit/*")
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
            "host_profile": {"provider": "", "layer": "profile_config", "surfaces": {}},
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
        "layer": "self_hosting_evidence",
        "gates": list(SELF_HOSTING_GATES),
        "toolchains": toolchains,
    }


def coupling_audit_report(root: Path) -> dict[str, Any]:
    release = _release_report(root)
    gaps = _vendor_term_gaps(root) + _gate_profile_gaps()
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "taxonomy": dict(COUPLING_LAYERS),
        "git_native": {
            "strongly_bound": True,
            "layer": "product_semantic",
            "allowed_terms": list(GIT_NATIVE_TERMS),
            "not_a_generic_vcs_abstraction": True,
        },
        "release_product_files": list(release["required_files"]),
        "release_host_profile": release["host_profile"],
        "self_hosting_toolchain": _self_hosting_toolchain(),
        "scanned_product_docs": [
            relative for relative in PRODUCT_SEMANTIC_DOCS if (root / relative).exists()
        ],
    }
