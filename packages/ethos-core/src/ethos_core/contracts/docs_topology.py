"""Documentation topology contract shared by ETHOS and governed repositories.

The contract is intentionally physical and adopter-neutral. It defines the
minimum documentation information architecture that should be recognizable in
any repository governed by ETHOS without forcing product-specific extension
roots such as ``docs/architecture`` or adopter-specific subject matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DOCS_ROOT_REQUIRED_PATHS: tuple[tuple[str, str], ...] = (
    ("docs/README.md", "documentation navigation and lane map"),
    ("docs/current/README.md", "implemented current contracts and runbooks"),
    ("docs/reference/README.md", "stable vocabulary, boundaries, and governance"),
    ("docs/evidence/README.md", "dated proof and scoped evidence"),
    ("docs/future/README.md", "target designs that are not current truth"),
    ("docs/history/README.md", "retired rationale and archival logs"),
)

DECISION_RECORD_REQUIRED_PATHS: tuple[tuple[str, str], ...] = (
    ("docs/decisions/README.md", "decision-record entrypoint"),
    ("docs/decisions/decision-index.md", "current accepted ruling index"),
    ("docs/decisions/decision-dependency-map.md", "decision dependency map"),
    ("docs/decisions/decision-code-links.md", "decision to code, test, and command links"),
    ("docs/decisions/accepted/README.md", "accepted decision records"),
    ("docs/decisions/superseded/README.md", "superseded decision records"),
    ("docs/decisions/templates/README.md", "decision-record template index"),
    ("docs/decisions/templates/decision-record.md", "decision-record template"),
)

CANONICAL_DOC_LANES: tuple[tuple[str, str], ...] = (
    ("current", "implemented contracts, runbooks, development rules"),
    ("decisions", "durable rulings with explicit scope and revisit trigger"),
    ("evidence", "dated proof, manifests, smoke notes, closeout records"),
    ("future", "target designs and roadmap material not yet current"),
    ("reference", "stable vocabulary, boundaries, governance references"),
    ("history", "retired rationale and archival logs"),
)

PRODUCT_EXTENSION_ROOTS = frozenset(
    {
        "docs/_meta",
        "docs/architecture",
        "docs/concepts",
        "docs/governance",
        "docs/plans",
        "docs/research",
        "docs/start",
    }
)

SUPPORTED_REPOSITORY_FORMS = ("single-repository", "monorepo", "multi-repository")


def normalize_docs_path(path: Path | str) -> str:
    """Return a repository-relative POSIX docs path without current-directory noise."""
    text = Path(path).as_posix()
    while text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def docs_topology_contract() -> dict[str, Any]:
    """Return the stable documentation topology contract."""
    required_paths = DOCS_ROOT_REQUIRED_PATHS + DECISION_RECORD_REQUIRED_PATHS
    return {
        "schema_version": 1,
        "principle": "high-isomorphism documentation kernel across governed repositories",
        "adopter_neutral": True,
        "requires_identical_subject_matter": False,
        "repository_form_invariant": True,
        "supported_repository_forms": list(SUPPORTED_REPOSITORY_FORMS),
        "required_paths": [
            {"path": path, "boundary": boundary} for path, boundary in required_paths
        ],
        "required_paths_by_repository_form": {
            form: [path for path, _boundary in required_paths]
            for form in SUPPORTED_REPOSITORY_FORMS
        },
        "decision_record_paths": [
            {"path": path, "boundary": boundary}
            for path, boundary in DECISION_RECORD_REQUIRED_PATHS
        ],
        "canonical_lanes": [
            {"lane": lane, "boundary": boundary} for lane, boundary in CANONICAL_DOC_LANES
        ],
        "product_extension_roots": sorted(PRODUCT_EXTENSION_ROOTS),
    }


def required_docs_topology_paths() -> tuple[str, ...]:
    """Return required repository-relative paths for the common docs kernel."""
    return tuple(
        path for path, _boundary in DOCS_ROOT_REQUIRED_PATHS + DECISION_RECORD_REQUIRED_PATHS
    )


def is_product_docs_extension_root(path: Path | str) -> bool:
    """Return whether a docs path is an ETHOS product extension, not common kernel."""
    rel = normalize_docs_path(path)
    return any(rel == root or rel.startswith(f"{root}/") for root in PRODUCT_EXTENSION_ROOTS)
