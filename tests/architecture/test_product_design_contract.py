"""Architecture boundaries not already owned by declarative repository gates."""

from __future__ import annotations

import shutil
from pathlib import Path

from ethos.repository.design.integrity import design_integrity_report

ROOT = Path(__file__).resolve().parents[2]
DESIGN_DOCUMENTS = (
    "README.md",
    "docs/concepts/kernel-model.md",
    "docs/governance/product-design-contract.md",
    "docs/reference/command-plane.md",
    "docs/reference/glossary.md",
    "system/axioms.md",
)


def _copy_design_documents(target: Path) -> tuple[str, ...]:
    for relative in DESIGN_DOCUMENTS:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    return DESIGN_DOCUMENTS


def _active_change_carriers() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (ROOT / "openspec/changes").iterdir()
        if path.is_dir() and path.name != "archive"
    )


def test_design_integrity_uses_supplied_tracked_documents_as_authority(
    tmp_path: Path,
) -> None:
    tracked = _copy_design_documents(tmp_path)
    rogue = tmp_path / "docs/rogue.md"
    rogue.write_text(
        "[Owner](governance/product-design-contract.md#semantic-kernel)\n",
        encoding="utf-8",
    )

    report = design_integrity_report(tmp_path, tracked_documents=tracked)

    assert report["verdict"] == "pass", report["required_gaps"]
    assert "docs/rogue.md" not in report["references"]


def test_current_change_uses_only_the_official_openspec_artifact_shape() -> None:
    changes = _active_change_carriers()

    assert len(changes) <= 1
    for change in changes:
        artifacts = {
            path.relative_to(change).as_posix() for path in change.rglob("*") if path.is_file()
        }
        unsupported = {
            artifact
            for artifact in artifacts
            if artifact not in {".openspec.yaml", "proposal.md", "design.md", "tasks.md"}
            and not (artifact.startswith("specs/") and artifact.endswith(".md"))
        }
        assert not unsupported
