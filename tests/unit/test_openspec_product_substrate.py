from __future__ import annotations

import tomllib
from pathlib import Path

from ethos.adapters import openspec
from ethos.repository.policy.schema import validate_schema_instance

ROOT = Path(__file__).resolve().parents[2]


def test_openspec_product_substrate_files_exist() -> None:
    required = [
        "openspec/README.md",
        "openspec/specs/README.md",
        "openspec/specs/families.toml",
        "openspec/specs/capability.template.toml",
        "openspec/changes/README.md",
        "openspec/changes/template.md",
    ]

    for relative in required:
        assert (ROOT / relative).is_file(), relative


def test_live_capability_profiles_declare_facets_and_validate() -> None:
    for path in sorted((ROOT / "openspec" / "specs").glob("*/capability.toml")):
        payload = tomllib.loads(path.read_text(encoding="utf-8"))

        assert payload["decision_axes"], path
        assert payload["recommended_facets"], path
        assert validate_schema_instance("capability-profile.schema.json", payload, root=ROOT)["ok"]


def test_lifecycle_reviews_all_active_changes_when_unspecified(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    for capability in ("ethos-repository", "ethos-contracts"):
        spec_dir = root / "openspec" / "specs" / capability
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text(f"# {capability}\n", encoding="utf-8")
        (spec_dir / "capability.toml").write_text(
            "\n".join(
                [
                    'family = "repository-governance"',
                    'primary_invariant = "sample"',
                    'routing_question = "sample?"',
                    'decision_axes = ["lifecycle", "surface", "authority"]',
                    'boundary_rules = ["sample"]',
                    "",
                    "[owner]",
                    f'package = "{capability}"',
                    'scope = "sample"',
                    "",
                    "[recommended_facets]",
                    'lifecycle = ["validation"]',
                    'surface = ["openspec"]',
                    'authority = ["openspec"]',
                    "",
                    "[proof_profile]",
                    'default_command = "ethos prove --json"',
                    'executed_command = "ethos prove --execute --json"',
                    'required_gates = ["claims"]',
                    "",
                ]
            ),
            encoding="utf-8",
        )
    (root / "openspec" / "config.yaml").write_text(
        "project: sample\nversion: 1\n",
        encoding="utf-8",
    )
    for change, capability in (
        ("change-one", "ethos-repository"),
        ("change-two", "ethos-contracts"),
    ):
        change_root = root / "openspec" / "changes" / change
        (change_root / "specs" / capability).mkdir(parents=True, exist_ok=True)
        (change_root / "proposal.md").write_text(
            "\n".join(
                [
                    "## Why",
                    "sample",
                    "",
                    "## Capabilities",
                    f"- `{capability}`: subject=sample; reuse=extend; change=modify; "
                    "facet:lifecycle=validation; facet:surface=openspec; "
                    "facet:authority=openspec",
                    "",
                    "## Out Of Scope",
                    "- sample",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (change_root / "design.md").write_text("## Design\nsample\n", encoding="utf-8")
        (change_root / "tasks.md").write_text("## Tasks\n- [ ] sample\n", encoding="utf-8")
        (change_root / "specs" / capability / "spec.md").write_text(
            "## ADDED Requirements\n\n"
            "### Requirement: Sample\n\n"
            "#### Scenario: Sample\n\n"
            "- **WHEN** sample\n"
            "- **THEN** sample\n",
            encoding="utf-8",
        )
    claims = root / "evidence" / "claims"
    claims.mkdir(parents=True)
    for change in ("change-one", "change-two"):
        (claims / f"{change}.toml").write_text(
            "\n".join(
                [
                    "[claim]",
                    f'id = "{change}"',
                    'state = "active"',
                    "",
                    "[carriers]",
                    f'openspec = "openspec/changes/{change}"',
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def fake_base_command() -> tuple[str, ...]:
        return ("openspec",)

    def fake_run_json(
        _root: Path,
        _base: tuple[str, ...],
        args: tuple[str, ...],
    ) -> dict[str, object]:
        if args == ("doctor", "--json"):
            payload: dict[str, object] = {"root": {"healthy": True}}
        elif args == ("list", "--json"):
            payload = {
                "changes": [
                    {"name": "change-one", "status": "in-progress"},
                    {"name": "change-two", "status": "in-progress"},
                ]
            }
        elif args[:3] == ("status", "--change", "change-one"):
            payload = {"isComplete": True, "schemaName": "spec-driven"}
        elif args == ("validate", "--all", "--strict", "--json"):
            payload = {"items": [], "summary": {"totals": {"failed": 0}}}
        else:
            payload = {}
        return {
            "command": ["openspec", *args],
            "exit_code": 0,
            "stdout": "{}",
            "stderr": "",
            "json": payload,
            "parse_error": "",
        }

    monkeypatch.setattr(openspec, "_openspec_base_command", fake_base_command)
    monkeypatch.setattr(openspec, "_run_json", fake_run_json)

    report = openspec.openspec_governance_report(root, lifecycle=True)

    assert report["ok"] is True
    assert [item["name"] for item in report["lifecycle"]["changes"]] == [
        "change-one",
        "change-two",
    ]
