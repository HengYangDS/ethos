"""Documentation topology contract shared by ETHOS and governed repositories.

The contract is intentionally physical and adopter-neutral. It defines the
minimal semantic documentation information architecture that should be
recognizable in any repository governed by ETHOS without encoding truth state in
path names such as ``docs/current`` or ``docs/future``. Truth state belongs in
front matter and evidence. Documentation is organized on two bound axes: a
directory names a document's SUBJECT domain, while its ``role`` front-matter
names the document's FUNCTION. The two are bound by a role->root law — kernel
roles (``ROLE_KERNEL_ROOTS``) enforced everywhere, plus per-repository extension
roots declared in the taxonomy — so a document's role must be legal for the
directory it lives in.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

DOCS_ROOT_REQUIRED_PATHS: tuple[tuple[str, str], ...] = (
    ("docs/README.md", "documentation navigation and lane map"),
    ("docs/reference/README.md", "stable vocabulary, boundaries, and command references"),
    ("docs/evidence/README.md", "dated proof and scoped evidence"),
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
    ("decisions", "durable rulings with explicit scope and revisit trigger"),
    ("evidence", "dated proof, manifests, smoke notes, closeout records"),
    ("reference", "stable vocabulary, boundaries, and governance references"),
    ("history", "retired rationale and archival logs"),
)

FORBIDDEN_DOCS_ROOTS = frozenset({"docs/current", "docs/future"})

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
STATE_VALUES = ("canonical", "active", "planned", "experimental", "superseded", "archived")

# Universal, adopter-neutral document role vocabulary. Every governed repository
# inherits this kernel set; a repository may ADD roles via its taxonomy but can
# never remove a kernel role. Roles name the FUNCTION of a document; directory
# names describe its SUBJECT domain. The two axes are bound by ROLE_KERNEL_ROOTS
# (kernel, below) and per-repository extension-root declarations.
ROLE_VALUES = (
    "index",
    "explanation",
    "reference",
    "decision",
    "policy",
    "evidence",
    "history",
    "template",
    "plan",
    "research",
    "findings",
    "progress",
    "ledger",
    "how-to",
)

# Kernel role -> the docs root(s) a document with that role MUST live under.
# These are the immutable warrant-type bindings enforced in every governed
# repository. Extension roles (explanation, policy, plan, ...) are bound per
# repository through the taxonomy's extension-root declarations, not here.
# `index` is intentionally absent: a README index is legal in any root.
ROLE_KERNEL_ROOTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("decision", ("docs/decisions",)),
    ("evidence", ("docs/evidence",)),
    ("history", ("docs/history",)),
    # reference lives in the reference lane, or alongside the decisions it
    # supports (decision-code-links, decision-dependency-map).
    ("reference", ("docs/reference", "docs/decisions")),
    # decision-record templates live under the decisions lane.
    ("template", ("docs/decisions",)),
)


def normalize_docs_path(path: Path | str) -> str:
    """Return a repository-relative POSIX docs path without current-directory noise."""
    return Path(path).as_posix().rstrip("/")


def docs_topology_contract() -> dict[str, Any]:
    """Return the stable documentation topology contract."""
    required_paths = DOCS_ROOT_REQUIRED_PATHS + DECISION_RECORD_REQUIRED_PATHS
    return {
        "schema_version": 1,
        "principle": "minimal semantic documentation kernel across governed repositories",
        "adopter_neutral": True,
        "requires_identical_subject_matter": False,
        "repository_form_invariant": True,
        "state_metadata_required": True,
        "time_state_directories_allowed": False,
        "supported_state_values": list(STATE_VALUES),
        "supported_role_values": list(ROLE_VALUES),
        "role_kernel_roots": {role: list(roots) for role, roots in ROLE_KERNEL_ROOTS},
        "forbidden_roots": sorted(FORBIDDEN_DOCS_ROOTS),
        "supported_repository_forms": list(SUPPORTED_REPOSITORY_FORMS),
        "required_paths": [
            {"path": path, "boundary": boundary} for path, boundary in required_paths
        ],
        # The required kernel is deliberately identical for every repository form
        # (single-repository, monorepo, multi-repository): the whole value of a
        # shared skeleton is that humans and agents recover the same lanes in any
        # governed repository without relearning its layout. `required_paths`
        # above is that single, form-invariant set; see `repository_form_invariant`.
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


def kernel_role_roots() -> dict[str, tuple[str, ...]]:
    """Map each kernel role to the docs root(s) a document with that role must use.

    These bindings are universal and adopter-neutral: every governed repository
    enforces them. Extension roles are bound per repository through the taxonomy.
    """
    return dict(ROLE_KERNEL_ROOTS)


def is_product_docs_extension_root(path: Path | str) -> bool:
    """Return whether a docs path is an ETHOS product extension, not common kernel."""
    rel = normalize_docs_path(path)
    return any(rel == root or rel.startswith(f"{root}/") for root in PRODUCT_EXTENSION_ROOTS)
