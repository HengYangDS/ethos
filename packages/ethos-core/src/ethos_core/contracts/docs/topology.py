"""Documentation topology contract shared by ETHOS and governed repositories.

The contract is intentionally physical and adopter-neutral. It defines the
minimum semantic documentation information architecture that should be
recognizable in any repository governed by ETHOS without encoding truth state in
path names such as ``docs/current`` or ``docs/future``. Truth state belongs in
front matter and evidence, while directory names describe semantic ownership.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DOCS_ROOT_REQUIRED_PATHS: tuple[tuple[str, str], ...] = (
    ("docs/README.md", "documentation navigation and semantic lane map"),
    ("docs/index.md", "audience-oriented documentation navigation"),
    ("docs/start/quickstart.md", "first-run workflow and command path"),
    ("docs/governance/README.md", "governance policy and operating model index"),
    ("docs/reference/README.md", "stable vocabulary, boundaries, and command reference"),
    ("docs/evidence/README.md", "dated proof and scoped evidence summaries"),
    ("docs/plans/README.md", "planned work and roadmap material with explicit state"),
    ("docs/history/README.md", "retired rationale and archival logs"),
)

DECISION_RECORD_REQUIRED_PATHS: tuple[tuple[str, str], ...] = (
    ("docs/decisions/README.md", "decision-record entrypoint"),
    ("docs/decisions/decision-index.md", "accepted ruling index"),
    ("docs/decisions/decision-dependency-map.md", "decision dependency map"),
    ("docs/decisions/decision-code-links.md", "decision to code, test, and command links"),
    ("docs/decisions/accepted/README.md", "accepted decision records"),
    ("docs/decisions/superseded/README.md", "superseded decision records"),
    ("docs/decisions/templates/README.md", "decision-record template index"),
    ("docs/decisions/templates/decision-record.md", "decision-record template"),
)

CANONICAL_DOC_LANES: tuple[tuple[str, str], ...] = (
    ("start", "operator entrypoints and first-run workflows"),
    ("governance", "policies, rules, and operating constraints"),
    ("decisions", "durable rulings with explicit scope and revisit trigger"),
    ("evidence", "dated proof, manifests, smoke notes, closeout records"),
    ("plans", "planned or research-backed work that is not authority until promoted"),
    ("reference", "stable vocabulary, boundaries, and governance references"),
    ("history", "retired rationale and archival logs"),
)

FORBIDDEN_DOCS_ROOTS = frozenset({"docs/current", "docs/future"})

PRODUCT_EXTENSION_ROOTS = frozenset(
    {
        "docs/_meta",
        "docs/architecture",
        "docs/concepts",
        "docs/research",
    }
)

SUPPORTED_REPOSITORY_FORMS = ("single-repository", "monorepo", "multi-repository")
STATE_VALUES = ("canonical", "active", "planned", "experimental", "superseded", "archived")


def normalize_docs_path(path: Path | str) -> str:
    """Return a repository-relative POSIX docs path without current-directory noise."""
    return Path(path).as_posix().rstrip("/")


def docs_topology_contract() -> dict[str, Any]:
    """Return the stable documentation topology contract."""
    required_paths = DOCS_ROOT_REQUIRED_PATHS + DECISION_RECORD_REQUIRED_PATHS
    return {
        "schema_version": 1,
        "principle": "semantic documentation kernel across governed repositories",
        "adopter_neutral": True,
        "requires_identical_subject_matter": False,
        "repository_form_invariant": True,
        "state_metadata_required": True,
        "time_state_directories_allowed": False,
        "supported_state_values": list(STATE_VALUES),
        "forbidden_roots": sorted(FORBIDDEN_DOCS_ROOTS),
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


def forbidden_docs_topology_roots() -> tuple[str, ...]:
    """Return forbidden docs roots that encode state as directory topology."""
    return tuple(sorted(FORBIDDEN_DOCS_ROOTS))


def is_product_docs_extension_root(path: Path | str) -> bool:
    """Return whether a docs path is an ETHOS product extension, not common kernel."""
    rel = normalize_docs_path(path)
    return any(rel == root or rel.startswith(f"{root}/") for root in PRODUCT_EXTENSION_ROOTS)
