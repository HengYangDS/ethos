"""Product-document coupling scans."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.coupling.contracts import PRODUCT_HOST_PROJECTION_TERMS
from ethos.repository.policy.coupling.contracts import PRODUCT_SEMANTIC_DOCS
from ethos.repository.policy.coupling.contracts import PRODUCT_VENDOR_TERMS

if TYPE_CHECKING:
    from pathlib import Path


def vendor_term_gaps(root: Path) -> list[str]:
    """Return product-doc gaps for forbidden vendor-center terminology."""
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


def host_projection_term_gaps(root: Path) -> list[str]:
    """Return product-doc gaps for host-projection UI terminology."""
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
