from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DESIGN_INTEGRITY_DOCS = (
    "docs/governance/product-design-contract.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/command-plane.md",
    "docs/architecture/runner-and-mutation.md",
)

DESIGN_INTEGRITY_REQUIRED_TERMS = {
    "docs/governance/product-design-contract.md": (
        "Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle",
        "not an external slogan",
        "one kernel keeps the center",
        "truth and projection remain separate",
        "adapters stay adapters",
        "Configuration follows separation of concerns, MECE, SSOT, and DRY",
        "OpenSpec remains mandatory governance, not a product substrate",
        "not a generic VCS abstraction",
        "status",
        "plan",
        "prove",
        "land",
        "publish",
    ),
    "docs/concepts/kernel-model.md": (
        "Root Interpretation Boundary",
        "not a translation of that text",
        "engineering compression",
        "which kernel object it projects",
    ),
    "docs/reference/command-plane.md": (
        "status",
        "plan",
        "prove",
        "land",
        "publish",
        "report",
        "adapter UI text is not product state",
    ),
    "docs/architecture/runner-and-mutation.md": (
        "target path",
        "repository root",
        "prewrite",
        "post-write audit",
        "ethos land --closeout",
        'remote_push = "not_performed"',
    ),
}

DESIGN_INTEGRITY_FORBIDDEN_TERMS = (
    "VendorTruthCenter",
    "product_self",
    "adopter_repository",
    "dual-posture",
)

DESIGN_INTEGRITY_FORBIDDEN_ROOT_PATHS = (
    "CLAUDE.md",
    ".claude",
    ".ethos/decomp-recipes",
    ".gitnexus",
)

DESIGN_INTEGRITY_VENDOR_TERMS = (
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


def _design_integrity_report(root: Path) -> dict[str, object]:
    """Audit canonical design docs for kernel and boundary regressions.

    This is deliberately a projection over existing canonical docs, not a new
    source of product truth. It catches small design drifts where the transition
    loop, root/axiom constraint, configuration separation, or provider boundary
    silently disappears while lower-level tests still pass.
    """
    required_gaps: list[str] = []
    forbidden_paths = [
        f"design_integrity_forbidden_projection_path:{path}"
        for path in DESIGN_INTEGRITY_FORBIDDEN_ROOT_PATHS
        if (root / path).exists()
    ]
    required_gaps.extend(forbidden_paths)
    files: dict[str, dict[str, object]] = {}
    for doc in DESIGN_INTEGRITY_DOCS:
        path = root / doc
        if not path.exists():
            gap = f"design_integrity_doc_missing:{doc}"
            required_gaps.append(gap)
            files[doc] = {"ok": False, "missing": [gap], "forbidden": [], "vendor_terms": []}
            continue
        text = path.read_text(encoding="utf-8")
        missing = [
            f"design_integrity_anchor_missing:{doc}:{term}"
            for term in DESIGN_INTEGRITY_REQUIRED_TERMS.get(doc, ())
            if term not in text
        ]
        forbidden = [
            f"design_integrity_forbidden_term:{doc}:{term}"
            for term in DESIGN_INTEGRITY_FORBIDDEN_TERMS
            if term in text
        ]
        vendor_terms = [
            f"design_integrity_vendor_center_leak:{doc}:{term}"
            for term in DESIGN_INTEGRITY_VENDOR_TERMS
            if term in text
        ]
        doc_gaps = missing + forbidden + vendor_terms
        required_gaps.extend(doc_gaps)
        files[doc] = {
            "ok": not doc_gaps,
            "missing": missing,
            "forbidden": forbidden,
            "vendor_terms": vendor_terms,
        }
    return {
        "ok": not required_gaps,
        "scope": "canonical_product_design_docs",
        "source_of_truth": "docs plus product-design-contract anchors",
        "not_a_truth_store": True,
        "forbidden_projection_paths": forbidden_paths,
        "files": files,
        "required_gaps": required_gaps,
    }


def _front_matter_ok(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    header = text.split("---", 2)[1]
    return all(f"{key}:" in header for key in ("subject", "role", "state", "relations"))
