"""Architecture boundaries not already owned by declarative repository gates."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ethos.contracts.semantic import Commitment
from ethos.repository.design.integrity import design_integrity_report
from ethos.repository.registry.docs.registry import build_docs_registry

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


def test_semantic_capabilities_keep_their_existing_authority_boundaries() -> None:
    """Topology convergence does not recreate or widen semantic carriers.

    The archived lineage Change is evidence of historical design, not a current
    runtime owner.  The current kernel and official OpenSpec tree remain the
    only sources available to current planning.
    """
    assert tuple(Commitment.model_fields) == ("schema_version", "id", "acceptance")

    lineage_spec = ROOT / "openspec/changes/archive/2026-08-22-change-lineage-dag"
    assert (lineage_spec / "specs/contracts/spec.md").is_file()
    assert (lineage_spec / "specs/repository-governance/spec.md").is_file()

    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert not any(
        path.startswith("src/ethos/adapters/openspec/change_lineage/") for path in tracked
    )
    assert not any(path.startswith("src/ethos/contracts/change_lineage/") for path in tracked)
    assert not any(
        path.endswith("commitment.toml")
        for path in tracked
        if path.startswith("openspec/changes/semantic-topology-convergence/")
    )

    active_paths = {
        path.relative_to(ROOT / "openspec/changes/semantic-topology-convergence").as_posix()
        for path in (ROOT / "openspec/changes/semantic-topology-convergence").rglob("*")
        if path.is_file()
    }
    assert active_paths <= {
        ".openspec.yaml",
        "proposal.md",
        "design.md",
        "tasks.md",
    } | {path for path in active_paths if path.startswith("specs/") and path.endswith(".md")}

    registry = build_docs_registry(ROOT)
    assert not any(entry["path"].startswith("openspec/changes/archive/") for entry in registry)
    assert not any(
        path.startswith("src/ethos/")
        and any(token in path for token in ("lineage", "hypothesis", "experiment"))
        for path in tracked
    )
