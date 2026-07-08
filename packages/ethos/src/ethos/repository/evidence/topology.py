from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.profile import profile_relative_root

if TYPE_CHECKING:
    from pathlib import Path

_ALLOWED_ROOT_FILES = ("README.md",)
_ALLOWED_ROOT_DIRS = ("claims", "chronicle", "parity")
_CURATED_PROFILE_ALLOWED_ROOT_FILES = ("README.md",)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def evidence_topology_report(root: Path) -> dict[str, Any]:
    """Report whether tracked evidence follows the kernel evidence layout.

    Args:
        root: Repository root whose `evidence/` tree should be inspected.

    Returns:
        A deterministic read model with layout metadata, counts, and required
        gaps. The report is read-only and does not claim proof freshness.
    """
    repo = root.resolve()
    evidence_root_relative = profile_relative_root(repo, "durable_evidence")
    evidence_root = repo / evidence_root_relative
    if evidence_root_relative == "docs/evidence":
        return _curated_profile_evidence_report(evidence_root, evidence_root_relative)
    return _kernel_evidence_report(evidence_root, evidence_root_relative)


def _kernel_evidence_report(evidence_root: Path, evidence_root_relative: str) -> dict[str, Any]:
    claims_root = evidence_root / "claims"
    chronicle_root = evidence_root / "chronicle"
    parity_root = evidence_root / "parity"
    gaps: list[str] = []

    if not evidence_root.exists():
        return {
            "ok": False,
            "required_gaps": ["evidence_root_missing"],
            "layout": _kernel_layout_payload(evidence_root_relative),
            "counts": {
                "claim_files": 0,
                "chronicle_records": 0,
                "parity_artifacts": 0,
            },
        }

    root_entries = sorted(evidence_root.iterdir(), key=lambda path: path.name)
    for path in root_entries:
        if path.is_file() and path.name not in _ALLOWED_ROOT_FILES:
            gaps.append(f"evidence_root_file_not_allowed:{path.name}")
        if path.is_dir() and path.name not in _ALLOWED_ROOT_DIRS:
            gaps.append(f"evidence_root_dir_not_allowed:{path.name}")

    claim_files = sorted(claims_root.glob("*.toml")) if claims_root.is_dir() else []
    nested_claim_files = sorted(claims_root.glob("*/*.toml")) if claims_root.is_dir() else []
    gaps.extend(
        f"evidence_claim_nested_file:{_relative(path, claims_root)}" for path in nested_claim_files
    )

    chronicle_records = sorted(chronicle_root.glob("*/*.md")) if chronicle_root.is_dir() else []
    flat_chronicle_markdown = sorted(chronicle_root.glob("*.md")) if chronicle_root.is_dir() else []
    gaps.extend(f"evidence_chronicle_flat_markdown:{path.name}" for path in flat_chronicle_markdown)

    parity_artifacts = sorted(parity_root.glob("*")) if parity_root.is_dir() else []

    for directory, gap in (
        (claims_root, "evidence_claims_root_missing"),
        (chronicle_root, "evidence_chronicle_root_missing"),
        (parity_root, "evidence_parity_root_missing"),
    ):
        if not directory.is_dir():
            gaps.append(gap)

    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "layout": _kernel_layout_payload(evidence_root_relative),
        "counts": {
            "claim_files": len(claim_files),
            "chronicle_records": len(chronicle_records),
            "parity_artifacts": len([path for path in parity_artifacts if path.is_file()]),
        },
    }


def _curated_profile_evidence_report(
    evidence_root: Path,
    evidence_root_relative: str,
) -> dict[str, Any]:
    gaps: list[str] = []
    if not evidence_root.exists():
        return {
            "ok": False,
            "required_gaps": ["evidence_root_missing"],
            "layout": _curated_profile_layout_payload(evidence_root_relative),
            "counts": {
                "claim_files": 0,
                "chronicle_records": 0,
                "parity_artifacts": 0,
                "curated_artifacts": 0,
            },
        }

    root_entries = sorted(evidence_root.iterdir(), key=lambda path: path.name)
    gaps.extend(
        f"evidence_root_file_not_allowed:{path.name}"
        for path in root_entries
        if path.is_file() and path.name not in _CURATED_PROFILE_ALLOWED_ROOT_FILES
    )

    curated_artifacts = [
        path
        for path in evidence_root.rglob("*")
        if path.is_file() and path.name not in _CURATED_PROFILE_ALLOWED_ROOT_FILES
    ]
    return {
        "ok": not gaps,
        "required_gaps": gaps,
        "layout": _curated_profile_layout_payload(evidence_root_relative),
        "counts": {
            "claim_files": 0,
            "chronicle_records": 0,
            "parity_artifacts": 0,
            "curated_artifacts": len(curated_artifacts),
        },
    }


def _kernel_layout_payload(root: str) -> dict[str, object]:
    return {
        "root": root,
        "allowed_root_files": list(_ALLOWED_ROOT_FILES),
        "allowed_root_dirs": list(_ALLOWED_ROOT_DIRS),
        "claims_root": f"{root}/claims",
        "chronicle_root": f"{root}/chronicle",
        "parity_root": f"{root}/parity",
    }


def _curated_profile_layout_payload(root: str) -> dict[str, object]:
    return {
        "root": root,
        "mode": "curated_profile_evidence",
        "allowed_root_files": list(_CURATED_PROFILE_ALLOWED_ROOT_FILES),
        "allowed_root_dirs": ["*"],
        "claims_root": "",
        "chronicle_root": "",
        "parity_root": "",
    }
