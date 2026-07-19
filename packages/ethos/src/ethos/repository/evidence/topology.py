from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps
from ethos_core.contracts.evidence.layout import EvidenceLayoutDeclaration
from ethos_core.contracts.evidence.layout import load_evidence_layout_declaration

if TYPE_CHECKING:
    from pathlib import Path


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def evidence_topology_report(root: Path) -> dict[str, Any]:
    """Report whether tracked evidence follows the declared evidence layout.

    Args:
        root: Repository root whose durable evidence tree should be inspected.

    Returns:
        A deterministic read model with declaration source refs, layout metadata,
        counts, and required gaps. The report is read-only and does not claim
        proof freshness.
    """
    repo = root.resolve()
    declaration = load_evidence_layout_declaration()
    profile = load_repository_profile(repo)
    if gaps := profile_required_gaps(profile):
        return {
            "ok": False,
            "required_gaps": list(gaps),
            "layout": declaration.layout_payload("evidence"),
            "counts": _empty_counts(),
        }
    evidence_root_relative = (
        profile.declaration.roots.durable_evidence if profile.declaration else "evidence"
    )
    evidence_root = repo / evidence_root_relative
    if evidence_root_relative == declaration.profile_curated_root:
        return _curated_profile_evidence_report(
            evidence_root,
            evidence_root_relative,
            declaration=declaration,
        )
    return _kernel_evidence_report(
        evidence_root,
        evidence_root_relative,
        declaration=declaration,
    )


def _empty_counts(*, curated_profile: bool = False) -> dict[str, int]:
    counts = {
        "claim_files": 0,
        "chronicle_records": 0,
        "parity_artifacts": 0,
    }
    if curated_profile:
        counts["curated_artifacts"] = 0
    return counts


def _kernel_evidence_report(
    evidence_root: Path,
    evidence_root_relative: str,
    *,
    declaration: EvidenceLayoutDeclaration,
) -> dict[str, Any]:
    kernel = declaration.kernel
    claims_root = evidence_root / "claims"
    chronicle_root = evidence_root / "chronicle"
    parity_root = evidence_root / "parity"
    gaps: list[str] = []

    if not evidence_root.exists():
        return {
            "ok": False,
            "required_gaps": [declaration.root_missing_gap],
            "layout": declaration.layout_payload(evidence_root_relative),
            "counts": _empty_counts(),
        }

    root_entries = sorted(evidence_root.iterdir(), key=lambda path: path.name)
    for path in root_entries:
        if path.is_file() and path.name not in kernel.allowed_root_files:
            gaps.append(f"{kernel.root_file_not_allowed_gap_prefix}:{path.name}")
        if path.is_dir() and path.name not in kernel.allowed_root_dirs:
            gaps.append(f"{kernel.root_dir_not_allowed_gap_prefix}:{path.name}")

    claim_files = sorted(claims_root.glob(kernel.claim_file_glob)) if claims_root.is_dir() else []
    nested_claim_files = (
        sorted(claims_root.glob(kernel.nested_claim_file_glob)) if claims_root.is_dir() else []
    )
    gaps.extend(
        f"{kernel.claim_nested_file_gap_prefix}:{_relative(path, claims_root)}"
        for path in nested_claim_files
    )

    chronicle_records = (
        sorted(chronicle_root.glob(kernel.chronicle_record_glob)) if chronicle_root.is_dir() else []
    )
    flat_chronicle_markdown = (
        sorted(chronicle_root.glob(kernel.flat_chronicle_glob)) if chronicle_root.is_dir() else []
    )
    gaps.extend(
        f"{kernel.chronicle_flat_markdown_gap_prefix}:{path.name}"
        for path in flat_chronicle_markdown
    )

    parity_artifacts = (
        sorted(parity_root.glob(kernel.parity_artifact_glob)) if parity_root.is_dir() else []
    )

    gaps.extend(
        item.gap for item in kernel.required_subroot if not (evidence_root / item.name).is_dir()
    )

    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "layout": declaration.layout_payload(evidence_root_relative),
        "counts": {
            "claim_files": len(claim_files),
            "chronicle_records": len(chronicle_records),
            "parity_artifacts": len([path for path in parity_artifacts if path.is_file()]),
        },
    }


def _curated_profile_evidence_report(
    evidence_root: Path,
    evidence_root_relative: str,
    *,
    declaration: EvidenceLayoutDeclaration,
) -> dict[str, Any]:
    curated = declaration.curated_profile
    gaps: list[str] = []
    if not evidence_root.exists():
        return {
            "ok": False,
            "required_gaps": [declaration.root_missing_gap],
            "layout": declaration.layout_payload(evidence_root_relative, curated_profile=True),
            "counts": _empty_counts(curated_profile=True),
        }

    root_entries = sorted(evidence_root.iterdir(), key=lambda path: path.name)
    gaps.extend(
        f"{curated.root_file_not_allowed_gap_prefix}:{path.name}"
        for path in root_entries
        if path.is_file() and path.name not in curated.allowed_root_files
    )

    curated_artifacts = [
        path
        for path in evidence_root.rglob("*")
        if path.is_file() and path.name not in curated.allowed_root_files
    ]
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "layout": declaration.layout_payload(evidence_root_relative, curated_profile=True),
        "counts": {
            "claim_files": 0,
            "chronicle_records": 0,
            "parity_artifacts": 0,
            "curated_artifacts": len(curated_artifacts),
        },
    }
