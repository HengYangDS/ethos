from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

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
SEMANTIC_ANCHORS = frozenset({"semantic-kernel", "model-promotion"})
KERNEL_FORMULA = (
    "(ChangeContract, RepositoryFacts, prior Attestations) -> PlanIR -> new Attestations"
)
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
MODEL_PROMOTION_RE = re.compile(r"model promotion", re.IGNORECASE)
ROOT_TITLE_RE = re.compile(r"^# 问道$", re.MULTILINE)


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
) -> dict[str, tuple[str, frozenset[str]]]:
    try:
        tracked = subprocess.run(
            ("git", "ls-files", "*.md"),
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        tracked = None
    relatives = (
        tracked.stdout.splitlines()
        if tracked is not None and tracked.returncode == 0
        else [path.relative_to(root).as_posix() for path in root.rglob("*.md")]
    )
    owner = (root / DESIGN_OWNER).resolve()
    documents: dict[str, tuple[str, frozenset[str]]] = {}
    for relative in sorted(set(relatives)):
        path = root / relative
        if not path.is_file() or not _current_carrier(relative, registry):
            continue
        text = path.read_text(encoding="utf-8")
        anchors = frozenset(
            fragment
            for target in LINK_RE.findall(text)
            for link, _, fragment in (target.partition("#"),)
            if link and "://" not in link and (path.parent / link).resolve() == owner
        )
        documents[relative] = (text, anchors)
    return documents


def _owner_verse(
    documents: dict[str, tuple[str, frozenset[str]]],
    registry: dict[str, dict[str, str]],
) -> tuple[list[str], list[str]]:
    owner = documents.get(DESIGN_OWNER)
    if owner is None:
        return [], [f"design_canonical_owner_missing:{DESIGN_OWNER}"]
    gaps = []
    owner_entry = registry.get(DESIGN_OWNER, {})
    if owner_entry.get("state") != "canonical" or "canonical_for:" not in owner_entry.get(
        "relations", ""
    ):
        gaps.append("design_canonical_owner_front_matter_invalid")
    lines = owner[0].splitlines()
    verse_lines: list[str] = []
    if "# 问道" in lines:
        for line in lines[lines.index("# 问道") + 1 :]:
            if line.startswith("> "):
                verse_lines.append(line.removeprefix("> ").strip())
            elif verse_lines and line.strip():
                break
    if not verse_lines:
        gaps.append("design_canonical_root_text_missing")
    return verse_lines, gaps


def _projection_gaps(
    documents: dict[str, tuple[str, frozenset[str]]],
    registry: dict[str, dict[str, str]],
) -> list[str]:
    gaps: list[str] = []
    for relative in REQUIRED_PROJECTIONS:
        document = documents.get(relative)
        if document is None:
            gaps.append(f"design_projection_missing:{relative}")
            continue
        text, anchors = document
        if not anchors.intersection(SEMANTIC_ANCHORS):
            gaps.append(f"design_projection_owner_link_missing:{relative}")
        if "Design status: projection." not in text:
            gaps.append(f"design_projection_status_missing:{relative}")
        if relative in METADATA_PROJECTIONS:
            entry = registry.get(relative, {})
            relations = entry.get("relations", "")
            projects_owner = "projects:" in relations and any(
                f"product-design-contract.md#{anchor}" in relations for anchor in SEMANTIC_ANCHORS
            )
            if entry.get("state") != "projection" or not projects_owner:
                gaps.append(f"design_projection_front_matter_invalid:{relative}")
            if "canonical_for:" in relations:
                gaps.append(f"design_projection_claims_canonical_authority:{relative}")
    return gaps


def _reference_gaps(
    documents: dict[str, tuple[str, frozenset[str]]], verse_lines: list[str]
) -> tuple[list[str], list[str]]:
    references: list[str] = []
    gaps: list[str] = []
    for relative, (text, anchors) in documents.items():
        if relative == DESIGN_OWNER:
            continue
        triggered = KERNEL_FORMULA in text or MODEL_PROMOTION_RE.search(text)
        owner_linked = bool(anchors.intersection(SEMANTIC_ANCHORS))
        if triggered or owner_linked:
            references.append(relative)
        if triggered and not owner_linked:
            gaps.append(f"design_reference_owner_link_missing:{relative}")
        if relative != ROOT_AXIOMS:
            if any(line in text for line in verse_lines):
                gaps.append(f"design_root_verse_duplicated:{relative}")
            if ROOT_TITLE_RE.search(text):
                gaps.append(f"design_root_title_duplicated:{relative}")
    return references, gaps


def _axioms_gaps(
    documents: dict[str, tuple[str, frozenset[str]]], verse_lines: list[str]
) -> list[str]:
    axioms = documents.get(ROOT_AXIOMS)
    if axioms is None:
        return [f"design_axioms_missing:{ROOT_AXIOMS}"]
    text, anchors = axioms
    gaps = []
    if "root-constraint" not in anchors:
        gaps.append("design_axioms_root_constraint_link_missing")
    gaps.extend(
        gap
        for phrase, gap in (
            ("machine-adjacent engineering reading", "design_axioms_derived_reading_missing"),
            (
                "does not create a second truth center",
                "design_axioms_second_truth_boundary_missing",
            ),
        )
        if phrase not in text
    )
    gaps.extend(
        f"design_axioms_term_missing:{term}"
        for term in ("ChangeContract", "Attestation", "proposition")
        if term not in text
    )
    if ROOT_TITLE_RE.search(text):
        gaps.append("design_axioms_duplicates_root_title")
    if any(line in text for line in verse_lines):
        gaps.append("design_axioms_duplicates_root_verse")
    return gaps


def design_integrity_report(root: Path) -> dict[str, object]:
    """Audit current structural design ownership and root-text boundaries."""
    forbidden_paths = [path for path in FORBIDDEN_ROOT_PATHS if (root / path).exists()]
    gaps = [f"design_integrity_forbidden_projection_path:{path}" for path in forbidden_paths]
    registry = {entry["path"]: entry for entry in build_docs_registry(root)}
    documents = _documents(root, registry)
    verse_lines, owner_gaps = _owner_verse(documents, registry)
    references, reference_gaps = _reference_gaps(documents, verse_lines)
    gaps.extend(owner_gaps)
    gaps.extend(_projection_gaps(documents, registry))
    gaps.extend(reference_gaps)
    gaps.extend(_axioms_gaps(documents, verse_lines))

    gaps = list(dict.fromkeys(gaps))
    return {
        "ok": not gaps,
        "semantic_equivalence": "not_evaluated",
        "references": sorted(references),
        "required_gaps": gaps,
    }


def front_matter_ok(path: Path) -> bool:
    """Return whether a required governance document has the ETHOS front matter."""
    if not path.exists():
        return False
    header = front_matter(path)
    return all(key in header for key in ("subject", "role", "state", "relations"))
