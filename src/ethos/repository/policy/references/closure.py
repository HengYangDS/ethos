"""Close observed product references against positive native ownership."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.references.declarations import native_owned_references
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_gaps
from ethos.repository.policy.references.observation import repository_reference_files

if TYPE_CHECKING:
    from pathlib import Path


def product_reference_gaps(
    allowed: dict[str, frozenset[str]],
    observed: dict[str, set[str]],
) -> list[str]:
    """Reject machine references outside one declared product closure."""
    return reference_gaps(allowed, observed)


def repository_product_reference_gaps(root: Path) -> list[str]:
    """Return references without a positive native owner."""
    allowed = native_owned_references(root)
    observed = product_references_from_files(
        repository_reference_files(root), root=root, include_declarations=False
    )
    return reference_gaps(allowed, observed)
