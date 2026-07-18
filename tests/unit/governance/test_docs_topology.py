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


def _write_profile_docs_topology_policy(root: Path, body: str) -> None:
    profile = root / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        """schema_version = 1
profile_id = \"sample-adopter\"
profile_version = \"1\"
ethos_contract_version = \"1\"

[roots]
docs = \"docs\"

"""
        + body,
        encoding="utf-8",
    )


def test_docs_topology_profile_declares_time_state_roots(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = \"adopter_declared_compatibility\"
time_state_roots = [\"docs/current\", \"docs/future\"]
compatibility_decision = \"docs/reference/documentation-information-architecture.md\"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/future").mkdir(parents=True)
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is True
    assert report["forbidden_roots"] == []
    assert report["required_gaps"] == []
    assert report["profile_policy"]["source"] == ".ethos/profile.toml"
    assert report["profile_policy"]["state_root_policy"] == "adopter_declared_compatibility"
    assert report["profile_policy"]["state_metadata_policy"] == "front_matter_state"
    assert report["profile_policy"]["time_state_roots"] == [
        "docs/current",
        "docs/future",
    ]
    assert (
        report["profile_policy"]["compatibility_decision"]
        == "docs/reference/documentation-information-architecture.md"
    )
    assert report["profile_policy"]["required_gaps"] == []
    assert report["time_state_roots"] == ["docs/current", "docs/future"]


def test_docs_topology_profile_legacy_policy_still_requires_kernel(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = \"adopter_declared_compatibility\"
time_state_roots = [\"docs/current\", \"docs/future\"]
compatibility_decision = \"docs/reference/documentation-information-architecture.md\"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/future").mkdir(parents=True)
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/decisions/decision-code-links.md").unlink()

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["forbidden_roots"] == []
    assert report["required_gaps"] == [
        "docs_topology_missing:docs/decisions/decision-code-links.md"
    ]


def test_docs_topology_profile_rejects_legacy_roots_without_decision(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = \"adopter_declared_compatibility\"
time_state_roots = [\"docs/current\"]
compatibility_decision = \"docs/reference/missing-ia.md\"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "docs_topology_profile_compatibility_decision_missing:docs/reference/missing-ia.md"
    ]


def test_docs_topology_profile_rejects_unlisted_time_state_root(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = \"adopter_declared_compatibility\"
time_state_roots = [\"docs/current\"]
compatibility_decision = \"docs/reference/documentation-information-architecture.md\"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/future").mkdir(parents=True)
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["time_state_roots"] == ["docs/current"]
    assert report["forbidden_roots"] == ["docs/future"]
    assert report["required_gaps"] == ["docs_topology_forbidden_time_state_root:docs/future"]


def _write_required_docs_with_status_lines(root: Path) -> None:
    for relative in required_docs_topology_paths():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        status = "reference" if relative.endswith("decision-record.md") else "index"
        path.write_text(f"# placeholder\n\nStatus: {status}\n", encoding="utf-8")


def test_docs_topology_status_line_requires_profile_mapping(tmp_path: Path) -> None:
    _write_required_docs_with_status_lines(tmp_path)

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["missing_required_state_count"] == len(required_docs_topology_paths())
    assert report["profile_policy"]["state_metadata_policy"] == "front_matter_state"


def test_docs_topology_profile_maps_legacy_status_line_to_state_metadata(
    tmp_path: Path,
) -> None:
    _write_required_docs_with_status_lines(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_metadata_policy = "front_matter_or_status_line"
status_field = "Status"
compatibility_decision = "docs/reference/documentation-information-architecture.md"

[docs_topology.state_value_map]
index = "canonical"
reference = "canonical"
""",
    )
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert report["summary"]["missing_required_state_count"] == 0
    assert report["profile_policy"]["state_metadata_policy"] == ("front_matter_or_status_line")
    assert report["state_metadata"]["state_by_path"]["docs/README.md"] == "canonical"
    assert report["state_metadata"]["status_by_path"]["docs/README.md"] == "index"
    assert (
        report["state_metadata"]["status_by_path"]["docs/decisions/templates/decision-record.md"]
        == "reference"
    )


def test_docs_topology_profile_reports_unmapped_required_legacy_status(
    tmp_path: Path,
) -> None:
    _write_required_docs_with_status_lines(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_metadata_policy = "front_matter_or_status_line"
status_field = "Status"
compatibility_decision = "docs/reference/documentation-information-architecture.md"

[docs_topology.state_value_map]
reference = "canonical"
""",
    )
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert "docs_topology_state_unmapped:docs/README.md:index" in report["required_gaps"]


def test_docs_topology_profile_rejects_unknown_policy_values(tmp_path: Path) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = "allow_anything"
state_metadata_policy = "status_anywhere"
""",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert (
        "docs_topology_profile_state_root_policy_invalid:allow_anything" in report["required_gaps"]
    )
    assert (
        "docs_topology_profile_state_metadata_policy_invalid:status_anywhere"
        in report["required_gaps"]
    )


def test_docs_topology_profile_rejects_path_escaping_compatibility_decision(
    tmp_path: Path,
) -> None:
    _write_required_docs(tmp_path)
    outside = tmp_path.parent / "outside-docs-ia.md"
    outside.write_text("# outside\n", encoding="utf-8")
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = "adopter_declared_compatibility"
time_state_roots = ["docs/current"]
compatibility_decision = "../outside-docs-ia.md"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "docs_topology_profile_compatibility_decision_outside_repo:../outside-docs-ia.md"
    ]


def test_docs_topology_profile_rejects_unknown_time_state_root(
    tmp_path: Path,
) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = "adopter_declared_compatibility"
time_state_roots = ["docs/current", "docs/archive"]
compatibility_decision = "docs/reference/documentation-information-architecture.md"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert report["time_state_roots"] == ["docs/current"]
    assert report["required_gaps"] == ["docs_topology_profile_time_state_root_invalid:docs/archive"]


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
        lambda _root, _required, _policy: {
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
        lambda _root, _required, _policy: {
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


def test_docs_topology_profile_accepts_previous_compatibility_aliases(
    tmp_path: Path,
) -> None:
    _write_required_docs(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_root_policy = "profile_declared_legacy"
legacy_time_state_roots = ["docs/current"]
state_metadata_policy = "front_matter_or_status_line"
legacy_status_field = "Status"
legacy_decision = "docs/reference/documentation-information-architecture.md"

[docs_topology.state_value_map]
index = "canonical"
""",
    )
    (tmp_path / "docs/current").mkdir(parents=True)
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is True
    assert report["profile_policy"]["state_root_policy"] == "adopter_declared_compatibility"
    assert report["profile_policy"]["time_state_roots"] == ["docs/current"]
    assert report["profile_policy"]["status_field"] == "Status"
    assert (
        report["profile_policy"]["compatibility_decision"]
        == "docs/reference/documentation-information-architecture.md"
    )


def test_docs_topology_profile_requires_decision_for_status_mapping(
    tmp_path: Path,
) -> None:
    _write_required_docs_with_status_lines(tmp_path)
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_metadata_policy = "front_matter_or_status_line"
status_field = "Status"

[docs_topology.state_value_map]
index = "canonical"
reference = "canonical"
""",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is False
    assert "docs_topology_profile_compatibility_decision_missing" in report["required_gaps"]


def test_docs_topology_profile_keeps_front_matter_state_over_status_line(
    tmp_path: Path,
) -> None:
    _write_required_docs_with_status_lines(tmp_path)
    (tmp_path / "docs/README.md").write_text(
        "---\nstate: active\n---\n# Docs\n\nStatus: index\n",
        encoding="utf-8",
    )
    _write_profile_docs_topology_policy(
        tmp_path,
        """[docs_topology]
state_metadata_policy = "front_matter_or_status_line"
status_field = "Status"
compatibility_decision = "docs/reference/documentation-information-architecture.md"

[docs_topology.state_value_map]
index = "canonical"
reference = "canonical"
""",
    )
    (tmp_path / "docs/reference/documentation-information-architecture.md").write_text(
        "---\nstate: canonical\nrole: reference\n---\n# local IA\n",
        encoding="utf-8",
    )

    report = docs_topology_report(tmp_path)

    assert report["ok"] is True
    assert report["state_metadata"]["state_by_path"]["docs/README.md"] == "active"
    assert report["state_metadata"]["status_by_path"]["docs/README.md"] == "index"


def test_unmapped_state_gap_entries_skip_malformed_entries() -> None:
    assert docs_topology_module._unmapped_state_gap_entries(
        {
            "unmapped_states": [
                None,
                {"path": "docs/README.md"},
                {"status": "index"},
                {"path": "docs/README.md", "status": "index"},
            ]
        }
    ) == [("docs/README.md", "index")]


def test_docs_status_scan_handles_missing_docs_and_markdown_directories(
    tmp_path: Path,
) -> None:
    assert docs_topology_module._docs_status_by_path(tmp_path, "Status") == {}

    (tmp_path / "docs/not-a-file.md").mkdir(parents=True)

    assert docs_topology_module._docs_status_by_path(tmp_path, "Status") == {}


def test_line_field_tolerates_missing_file(tmp_path: Path) -> None:
    assert docs_topology_module._line_field(tmp_path / "missing.md", "Status:") == ""
