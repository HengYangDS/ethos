"""Architecture boundaries not already owned by declarative repository gates."""

from __future__ import annotations

import shutil
import tomllib
from graphlib import TopologicalSorter
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


def test_current_change_graph_is_at_most_one_bounded_and_acyclic() -> None:
    carriers = _active_change_carriers()
    commitments = {
        payload["id"]: (carrier, payload)
        for carrier in carriers
        for payload in (tomllib.loads((carrier / "commitment.toml").read_text(encoding="utf-8")),)
    }
    graph = {
        change_id: {
            item["target"]
            for item in payload.get("dependencies", ())
            if item.get("target", "").startswith("change:")
        }
        for change_id, (_carrier, payload) in commitments.items()
    }

    assert len(carriers) <= 1
    assert set().union(*graph.values()) <= set(graph)
    assert set(TopologicalSorter(graph).static_order()) == set(graph)
    if not commitments:
        return
    change_id, (carrier, _payload) = next(iter(commitments.items()))
    assert change_id == f"change:{carrier.name}"
