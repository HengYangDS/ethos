from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.evidence.layout import EvidenceLayoutDeclaration
from ethos.contracts.evidence.layout import load_evidence_layout_declaration
from ethos.contracts.verdict import close_verdict
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps

if TYPE_CHECKING:
    from pathlib import Path


def evidence_topology_report(root: Path) -> dict[str, Any]:
    """Report whether tracked evidence follows the declared evidence layout."""
    repo = root.resolve()
    declaration = load_evidence_layout_declaration()
    profile = load_repository_profile(repo)
    if gaps := profile_required_gaps(profile):
        return {
            "verdict": "block",
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
        "attestation_files": 0,
        "historical_artifacts": 0,
    }
    if curated_profile:
        counts["curated_artifacts"] = 0
    return counts


def _files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file()) if root.is_dir() else []


def _kernel_evidence_report(
    evidence_root: Path,
    evidence_root_relative: str,
    *,
    declaration: EvidenceLayoutDeclaration,
) -> dict[str, Any]:
    kernel = declaration.kernel
    gaps: list[str] = []

    if not evidence_root.exists():
        return {
            "verdict": "block",
            "required_gaps": [declaration.root_missing_gap],
            "layout": declaration.layout_payload(evidence_root_relative),
            "counts": _empty_counts(),
        }

    allowed_dirs = {*kernel.allowed_root_dirs, *kernel.historical_root_dirs}
    for item in sorted(evidence_root.iterdir(), key=lambda path: path.name):
        if item.is_file() and item.name not in kernel.allowed_root_files:
            gaps.append(f"{kernel.root_file_not_allowed_gap_prefix}:{item.name}")
        if item.is_dir() and item.name not in allowed_dirs:
            gaps.append(f"{kernel.root_dir_not_allowed_gap_prefix}:{item.name}")

    attestation_files = _files(evidence_root / kernel.allowed_root_dirs[0])
    historical_artifacts = sum(
        len(_files(evidence_root / directory)) for directory in kernel.historical_root_dirs
    )
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "required_gaps": gaps,
        "layout": declaration.layout_payload(evidence_root_relative),
        "counts": {
            "attestation_files": len(attestation_files),
            "historical_artifacts": historical_artifacts,
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
            "verdict": "block",
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
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "required_gaps": gaps,
        "layout": declaration.layout_payload(evidence_root_relative, curated_profile=True),
        "counts": {
            "attestation_files": len(_files(evidence_root / "attestations")),
            "historical_artifacts": 0,
            "curated_artifacts": len(curated_artifacts),
        },
    }
