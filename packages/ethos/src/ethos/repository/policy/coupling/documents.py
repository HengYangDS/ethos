"""Product-document coupling scans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_core.contracts.registry.declarations import load_coupling_declaration

if TYPE_CHECKING:
    from pathlib import Path


def vendor_term_gaps(root: Path) -> list[str]:
    """Return product-doc gaps for forbidden vendor-center terminology."""
    declaration = load_coupling_declaration()
    gaps: list[str] = []
    for relative in declaration.product_semantic_docs:
        path = root / relative
        if path.exists():
            text = path.read_text(encoding="utf-8")
            gaps.extend(
                f"product_vendor_term:{relative}:{term}"
                for term in declaration.product_vendor_terms
                if term in text
            )
    return gaps


def host_projection_term_gaps(root: Path) -> list[str]:
    """Return product-doc gaps for host-projection UI terminology."""
    declaration = load_coupling_declaration()
    gaps: list[str] = []
    for relative in declaration.product_semantic_docs:
        path = root / relative
        if path.exists():
            text = path.read_text(encoding="utf-8")
            gaps.extend(
                f"product_host_projection_term:{relative}:{term}"
                for term in declaration.product_host_projection_terms
                if term in text
            )
    return gaps
