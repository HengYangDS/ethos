from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ethos.contracts.verdict import close_verdict
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.repository.registry.docs.registry import front_matter

if TYPE_CHECKING:
    from pathlib import Path

DESIGN_OWNER = "docs/governance/product-design-contract.md"
ROOT_AXIOMS = "system/axioms.md"
REQUIRED_PROJECTIONS = (
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/reference/glossary.md",
    "docs/reference/command-plane.md",
)
METADATA_PROJECTIONS = frozenset(REQUIRED_PROJECTIONS) - {"README.md"}
REQUIRED_OWNER_ANCHORS = frozenset(
    {
        "semantic-kernel",
        "model-promotion",
        "invalid-state-taxonomy",
        "git-native-repository-substrate",
        "isomorphic-adopter-governance",
        "feedback-intent-preservation",
        "projection-homomorphism",
    }
)
REQUIRED_PROJECTION_ANCHOR = "semantic-kernel"
FORBIDDEN_ROOT_PATHS = (
    "CLAUDE.md",
    ".claude",
    ".ethos/decomp-recipes",
    ".gitnexus",
    "docs/superpowers",
)
EXCLUDED_PARTS = frozenset(
    {"_generated", "generated", "build", "dist", "runtime", ".cache", "__pycache__"}
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _slug(heading: str) -> str:
    """Return the CommonMark-compatible anchor grammar used by this contract."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", heading.lower())).strip("-")


def _anchors(text: str) -> frozenset[str]:
    return frozenset(_slug(match.group(2)) for match in HEADING_RE.finditer(text))


def _owner_links(path: Path, text: str, owner: Path) -> frozenset[str]:
    """Return structural fragment links from one document to the canonical owner."""
    return frozenset(
        fragment
        for target in LINK_RE.findall(text)
        for link, marker, fragment in (target.partition("#"),)
        if marker and link and "://" not in link and (path.parent / link).resolve() == owner
    )


def _current_carrier(relative: str, registry: dict[str, dict[str, str]]) -> bool:
    parts = relative.split("/")
    if (
        relative.startswith(("evidence/", "docs/evidence/", "openspec/changes/archive/"))
        or EXCLUDED_PARTS.intersection(parts)
        or registry.get(relative, {}).get("state") in {"archived", "superseded"}
    ):
        return False
    return (
        "/" not in relative
        or relative.startswith(
            ("docs/", "rules/", ".agents/skills/", "openspec/specs/", "openspec/changes/")
        )
        or relative in {"openspec/README.md", ROOT_AXIOMS}
    )


def _documents(
    root: Path,
    registry: dict[str, dict[str, str]],
    tracked_documents: tuple[str, ...],
) -> dict[str, tuple[Path, str, frozenset[str]]]:
    documents: dict[str, tuple[Path, str, frozenset[str]]] = {}
    for relative in sorted(set(tracked_documents)):
        path = root / relative
        if path.is_file() and _current_carrier(relative, registry):
            text = path.read_text(encoding="utf-8")
            documents[relative] = (path, text, _anchors(text))
    return documents


def _owner_gaps(
    documents: dict[str, tuple[Path, str, frozenset[str]]],
    registry: dict[str, dict[str, str]],
) -> list[str]:
    document = documents.get(DESIGN_OWNER)
    if document is None:
        return [f"design_canonical_owner_missing:{DESIGN_OWNER}"]
    _, _, anchors = document
    entry = registry.get(DESIGN_OWNER, {})
    gaps = []
    if entry.get("state") != "canonical" or "canonical_for:" not in entry.get("relations", ""):
        gaps.append("design_canonical_owner_front_matter_invalid")
    gaps.extend(
        f"design_canonical_owner_anchor_missing:{anchor}"
        for anchor in sorted(REQUIRED_OWNER_ANCHORS - anchors)
    )
    return gaps


def _projection_gaps(
    root: Path,
    documents: dict[str, tuple[Path, str, frozenset[str]]],
    registry: dict[str, dict[str, str]],
) -> list[str]:
    owner = (root / DESIGN_OWNER).resolve()
    gaps: list[str] = []
    for relative in REQUIRED_PROJECTIONS:
        document = documents.get(relative)
        if document is None:
            gaps.append(f"design_projection_missing:{relative}")
            continue
        path, text, _ = document
        if REQUIRED_PROJECTION_ANCHOR not in _owner_links(path, text, owner):
            gaps.append(f"design_projection_owner_link_missing:{relative}")
        if relative in METADATA_PROJECTIONS:
            entry = registry.get(relative, {})
            relation = entry.get("relations", "")
            if (
                entry.get("state") != "active"
                or f"product-design-contract.md#{REQUIRED_PROJECTION_ANCHOR}" not in relation
                or "canonical_for:" in relation
            ):
                gaps.append(f"design_projection_front_matter_invalid:{relative}")
    return gaps


def _reference_gaps(
    root: Path,
    documents: dict[str, tuple[Path, str, frozenset[str]]],
) -> tuple[list[str], list[str]]:
    owner = (root / DESIGN_OWNER).resolve()
    references: list[str] = []
    gaps: list[str] = []
    for relative, (path, text, _) in documents.items():
        if relative == DESIGN_OWNER:
            continue
        links = _owner_links(path, text, owner)
        if not links:
            raw_links = frozenset(
                fragment
                for target in LINK_RE.findall(text)
                for _, marker, fragment in (target.partition("#"),)
                if marker and fragment in REQUIRED_OWNER_ANCHORS
            )
            links = raw_links
        if links:
            references.append(relative)
    return references, gaps


def _axiom_gaps(root: Path, documents: dict[str, tuple[Path, str, frozenset[str]]]) -> list[str]:
    document = documents.get(ROOT_AXIOMS)
    if document is None:
        return [f"design_axioms_missing:{ROOT_AXIOMS}"]
    path, text, _ = document
    metadata = front_matter(path)
    owner = (root / DESIGN_OWNER).resolve()
    root_link = "root-constraint" in _owner_links(path, text, owner)
    gaps = []
    if "derives: ../docs/governance/product-design-contract.md#root-constraint" not in metadata.get(
        "relations", ""
    ):
        gaps.append("design_axioms_derivation_metadata_invalid")
    if not root_link:
        gaps.append("design_axioms_root_constraint_link_missing")
    if "second semantic owner" not in text:
        gaps.append("design_axioms_derivation_boundary_missing")
    gaps.extend(
        f"design_axioms_term_missing:{term}"
        for term in ("Commitment", "Attestation", "proposition")
        if term not in text
    )
    owner_text = (root / DESIGN_OWNER).read_text(encoding="utf-8")
    verse_lines = [
        line.removeprefix("> ").strip() for line in owner_text.splitlines() if line.startswith("> ")
    ]
    if any(line in text for line in verse_lines):
        gaps.append("design_axioms_duplicates_root_verse")
    return gaps


def design_integrity_report(
    root: Path,
    *,
    tracked_documents: tuple[str, ...] = (),
) -> dict[str, object]:
    """Audit design ownership, relation grammar, and derivation boundaries."""
    forbidden_paths = [path for path in FORBIDDEN_ROOT_PATHS if (root / path).exists()]
    gaps = [f"design_integrity_forbidden_projection_path:{path}" for path in forbidden_paths]
    registry = {entry["path"]: entry for entry in build_docs_registry(root)}
    documents = _documents(root, registry, tracked_documents)
    references, reference_gaps = _reference_gaps(root, documents)
    gaps.extend(_owner_gaps(documents, registry))
    gaps.extend(_projection_gaps(root, documents, registry))
    gaps.extend(reference_gaps)
    gaps.extend(_axiom_gaps(root, documents))
    required_gaps = list(dict.fromkeys(gaps))
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required_gaps)),
        "semantic_equivalence": "not_evaluated",
        "references": sorted(references),
        "required_gaps": required_gaps,
    }


def front_matter_ok(path: Path) -> bool:
    """Return whether a required governance document has the ETHOS front matter."""
    if not path.exists():
        return False
    header = front_matter(path)
    return all(key in header for key in ("subject", "role", "state", "relations"))
