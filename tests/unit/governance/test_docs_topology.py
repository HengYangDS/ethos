from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.docs_topology import docs_topology_report
from ethos_core.contracts.docs_topology import docs_topology_contract
from ethos_core.contracts.docs_topology import is_product_docs_extension_root
from ethos_core.contracts.docs_topology import normalize_docs_path
from ethos_core.contracts.docs_topology import required_docs_topology_paths

if TYPE_CHECKING:
    from pathlib import Path


def test_docs_topology_contract_declares_common_kernel() -> None:
    contract = docs_topology_contract()

    assert contract["adopter_neutral"] is True
    assert contract["requires_identical_subject_matter"] is False
    assert contract["repository_form_invariant"] is True
    assert {"single-repository", "monorepo", "multi-repository"} <= set(
        contract["supported_repository_forms"]
    )
    required = {item["path"] for item in contract["required_paths"]}
    assert {
        "docs/README.md",
        "docs/current/README.md",
        "docs/decisions/README.md",
        "docs/decisions/decision-index.md",
        "docs/decisions/decision-dependency-map.md",
        "docs/decisions/decision-code-links.md",
        "docs/decisions/accepted/README.md",
        "docs/decisions/superseded/README.md",
        "docs/decisions/templates/README.md",
        "docs/decisions/templates/decision-record.md",
        "docs/evidence/README.md",
        "docs/future/README.md",
        "docs/history/README.md",
        "docs/reference/README.md",
    } <= required
    assert "docs/architecture" in contract["product_extension_roots"]


def test_docs_topology_required_paths_are_repository_form_invariant() -> None:
    contract = docs_topology_contract()
    required = tuple(item["path"] for item in contract["required_paths"])

    for form, paths in contract["required_paths_by_repository_form"].items():
        assert form in contract["supported_repository_forms"]
        assert tuple(paths) == required


def test_docs_topology_path_helpers_normalize_and_classify_extensions() -> None:
    assert normalize_docs_path("./docs/architecture/") == "docs/architecture"
    assert normalize_docs_path("docs/current/README.md") == "docs/current/README.md"
    assert is_product_docs_extension_root("./docs/architecture/details.md") is True
    assert is_product_docs_extension_root("docs/current/README.md") is False


def test_docs_topology_report_accepts_product_docs_kernel() -> None:
    from pathlib import Path

    report = docs_topology_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["summary"]["missing_required_path_count"] == 0
    assert "docs/architecture" in report["product_extension_roots"]


def test_docs_topology_report_blocks_missing_decision_kernel(tmp_path: Path) -> None:
    for relative in required_docs_topology_paths():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# placeholder\n", encoding="utf-8")
    (tmp_path / "docs/decisions/decision-code-links.md").unlink()

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["missing_paths"] == ["docs/decisions/decision-code-links.md"]
    assert report["required_gaps"] == [
        "docs_topology_missing:docs/decisions/decision-code-links.md"
    ]
