from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.docs import topology as docs_topology_module
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos_core.contracts.docs.topology import docs_topology_contract
from ethos_core.contracts.docs.topology import forbidden_docs_topology_roots
from ethos_core.contracts.docs.topology import is_product_docs_extension_root
from ethos_core.contracts.docs.topology import normalize_docs_path
from ethos_core.contracts.docs.topology import required_docs_topology_paths

if TYPE_CHECKING:
    from pathlib import Path


def _write_required_docs(root: Path) -> None:
    for relative in required_docs_topology_paths():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---\nstate: canonical\n---\n# placeholder\n", encoding="utf-8")


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
        "docs/decisions/README.md",
        "docs/decisions/decision-index.md",
        "docs/decisions/decision-dependency-map.md",
        "docs/decisions/decision-code-links.md",
        "docs/decisions/accepted/README.md",
        "docs/decisions/superseded/README.md",
        "docs/decisions/templates/README.md",
        "docs/decisions/templates/decision-record.md",
        "docs/evidence/README.md",
        "docs/history/README.md",
        "docs/reference/README.md",
    } == required
    assert contract["time_state_directories_allowed"] is False
    assert set(contract["forbidden_roots"]) == {"docs/current", "docs/future"}
    lanes = {entry["lane"] for entry in contract["canonical_lanes"]}
    assert {"decisions", "evidence", "reference", "history"} == lanes
    assert {
        "docs/_meta",
        "docs/architecture",
        "docs/concepts",
        "docs/governance",
        "docs/plans",
        "docs/research",
        "docs/start",
    } <= set(contract["product_extension_roots"])


def test_docs_topology_required_paths_are_repository_form_invariant() -> None:
    contract = docs_topology_contract()

    # The kernel is one form-invariant set, not a per-form mapping that pretends
    # to vary. The contract states the invariant explicitly and exposes a single
    # required_paths list that applies to every supported repository form.
    assert contract["repository_form_invariant"] is True
    assert "required_paths_by_repository_form" not in contract
    assert len(contract["required_paths"]) == len(required_docs_topology_paths())
    assert {"single-repository", "monorepo", "multi-repository"} <= set(
        contract["supported_repository_forms"]
    )


def test_docs_topology_product_extension_roots_are_not_required_kernel() -> None:
    contract = docs_topology_contract()
    required = {item["path"] for item in contract["required_paths"]}
    extensions = set(contract["product_extension_roots"])

    assert {
        "docs/architecture",
        "docs/concepts",
        "docs/governance",
        "docs/plans",
        "docs/research",
        "docs/start",
    } <= extensions
    assert not any(path.startswith(tuple(f"{root}/" for root in extensions)) for path in required)


def test_docs_topology_path_helpers_normalize_and_classify_extensions() -> None:
    assert normalize_docs_path("./docs/architecture/") == "docs/architecture"
    assert normalize_docs_path("././docs/architecture/") == "docs/architecture"
    assert normalize_docs_path("docs/governance/README.md") == "docs/governance/README.md"
    assert is_product_docs_extension_root("./docs/architecture/details.md") is True
    assert is_product_docs_extension_root("docs/governance/README.md") is True
    assert is_product_docs_extension_root("docs/reference/README.md") is False


def test_docs_topology_report_accepts_product_docs_kernel() -> None:
    from pathlib import Path

    report = docs_topology_report(Path.cwd())

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["summary"]["missing_required_path_count"] == 0
    assert "docs/architecture" in report["product_extension_roots"]


def test_docs_topology_forbidden_roots_are_part_of_contract() -> None:
    assert set(forbidden_docs_topology_roots()) == {"docs/current", "docs/future"}


def test_docs_topology_report_blocks_missing_decision_kernel(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    (tmp_path / "docs/decisions/decision-code-links.md").unlink()

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["missing_paths"] == ["docs/decisions/decision-code-links.md"]
    assert report["required_gaps"] == [
        "docs_topology_missing:docs/decisions/decision-code-links.md"
    ]


def test_docs_topology_report_blocks_time_state_roots(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/future").mkdir(parents=True)

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["forbidden_roots"] == ["docs/current", "docs/future"]
    assert report["required_gaps"] == [
        "docs_topology_forbidden_time_state_root:docs/current",
        "docs_topology_forbidden_time_state_root:docs/future",
    ]


def test_docs_topology_report_blocks_missing_required_state(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    (tmp_path / "docs/reference/README.md").write_text("# reference\n", encoding="utf-8")

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["missing_required_state_count"] == 1
    assert report["required_gaps"] == ["docs_topology_state_missing:docs/reference/README.md"]


def test_docs_topology_report_rejects_current_future_state_values(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    path = tmp_path / "docs/reference/current.md"
    path.write_text("---\nstate: current\n---\n# bad state\n", encoding="utf-8")

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["invalid_state_count"] == 1
    assert report["required_gaps"] == [
        "docs_topology_state_invalid:docs/reference/current.md:current"
    ]


def test_docs_topology_report_blocks_kernel_role_in_wrong_root(tmp_path: Path) -> None:
    # A kernel role (decision) is bound to docs/decisions/ everywhere; placing a
    # decision-role document under docs/reference/ is an enforced mismatch.
    _write_required_docs(tmp_path)
    path = tmp_path / "docs/reference/stray-ruling.md"
    path.write_text("---\nstate: canonical\nrole: decision\n---\n# stray\n", encoding="utf-8")

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["role_root_mismatch_count"] == 1
    assert (
        "docs_topology_role_root_mismatch:docs/reference/stray-ruling.md:decision:docs/reference"
        in report["required_gaps"]
    )


def test_docs_topology_report_blocks_role_illegal_for_extension_root(tmp_path: Path) -> None:
    # An extension root only accepts the roles its taxonomy declares; an
    # undeclared (root, role) pair is a mismatch. Here architecture/ accepts
    # explanation and reference but not how-to.
    _write_required_docs(tmp_path)
    (tmp_path / "docs/_meta").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/_meta/taxonomy.toml").write_text(
        '[extension_roots]\n"docs/architecture" = ["explanation", "reference"]\n',
        encoding="utf-8",
    )
    path = tmp_path / "docs/architecture/walkthrough.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nstate: active\nrole: how-to\n---\n# walk\n", encoding="utf-8")

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert (
        "docs_topology_role_root_mismatch:docs/architecture/walkthrough.md:how-to:docs/architecture"
        in report["required_gaps"]
    )


def test_docs_topology_report_allows_index_role_in_any_root(tmp_path: Path) -> None:
    # A README index is legal in every root regardless of the root's role law.
    _write_required_docs(tmp_path)
    path = tmp_path / "docs/architecture/README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nstate: canonical\nrole: index\n---\n# index\n", encoding="utf-8")

    report = docs_topology_report(tmp_path)

    assert report["summary"]["role_root_mismatch_count"] == 0


def test_extension_root_law_ignores_malformed_taxonomy(tmp_path: Path) -> None:
    meta = tmp_path / "docs/_meta"
    meta.mkdir(parents=True)
    # Not valid TOML -> empty law.
    (meta / "taxonomy.toml").write_text("[extension_roots\n", encoding="utf-8")
    assert docs_topology_module._extension_root_law(tmp_path) == {}


def test_extension_root_law_ignores_non_table_section(tmp_path: Path) -> None:
    meta = tmp_path / "docs/_meta"
    meta.mkdir(parents=True)
    (meta / "taxonomy.toml").write_text('extension_roots = "nope"\n', encoding="utf-8")
    assert docs_topology_module._extension_root_law(tmp_path) == {}


def test_extension_root_law_skips_non_list_role_entries(tmp_path: Path) -> None:
    meta = tmp_path / "docs/_meta"
    meta.mkdir(parents=True)
    (meta / "taxonomy.toml").write_text(
        '[extension_roots]\n"docs/architecture" = ["explanation"]\n"docs/bad" = "not-a-list"\n',
        encoding="utf-8",
    )
    law = docs_topology_module._extension_root_law(tmp_path)
    assert law == {"docs/architecture": {"explanation"}}


def test_root_of_handles_top_level_docs_file() -> None:
    assert docs_topology_module._root_of("docs/README.md") == "docs"
    assert docs_topology_module._root_of("docs/architecture/x.md") == "docs/architecture"


def test_docs_topology_report_tolerates_malformed_internal_state_shape(
    tmp_path: Path, monkeypatch
) -> None:
    _write_required_docs(tmp_path)

    monkeypatch.setattr(
        docs_topology_module,
        "_state_metadata_report",
        lambda _root, _required: {
            "missing_required_state_paths": "not-a-list",
            "invalid_states": "not-a-list",
        },
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_docs_topology_report_skips_malformed_invalid_state_entries(
    tmp_path: Path, monkeypatch
) -> None:
    _write_required_docs(tmp_path)

    monkeypatch.setattr(
        docs_topology_module,
        "_state_metadata_report",
        lambda _root, _required: {
            "missing_required_state_paths": [],
            "invalid_states": [
                None,
                {"path": "docs/missing-state.md"},
                {"state": "current"},
                {"path": "docs/reference/current.md", "state": "current"},
            ],
        },
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "docs_topology_state_invalid:docs/reference/current.md:current"
    ]


def test_docs_topology_state_scan_ignores_markdown_directories(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    (tmp_path / "docs/not-a-file.md").mkdir()

    report = docs_topology_report(tmp_path)

    assert report["ok"] is True
    assert "docs/not-a-file.md" not in report["state_metadata"]["state_by_path"]


def test_docs_topology_front_matter_state_edge_cases(tmp_path: Path) -> None:
    closed_without_state = tmp_path / "closed.md"
    closed_without_state.write_text("---\nsubject: sample\n---\n# Closed\n", encoding="utf-8")
    unclosed_without_state = tmp_path / "unclosed.md"
    unclosed_without_state.write_text("---\nsubject: sample\n# Unclosed\n", encoding="utf-8")

    assert docs_topology_module._front_matter_state(closed_without_state) == ""
    assert docs_topology_module._front_matter_state(unclosed_without_state) == ""
    assert docs_topology_module._front_matter_state(tmp_path / "missing.md") == ""
