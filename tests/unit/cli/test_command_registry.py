from __future__ import annotations

from pathlib import Path

from ethos.repository.registry.commands import command_registry_report
from ethos.repository.registry.commands import public_commands
from ethos.repository.registry.docs.commands import command_examples_report


def test_command_registry_separates_public_workflow_from_maintainer_reference() -> None:
    report = command_registry_report()

    assert public_commands() == (
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    )
    assert report["public_workflow_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert report["reader_view_commands"] == ["ethos orient"]
    assert report["scorecard_commands"] == ["ethos report"]
    assert report["setup_commands"] == [
        "ethos init",
        "ethos adopt",
        "ethos doctor",
    ]
    assert "ethos orient" not in report["public_workflow_commands"]
    assert "ethos report" not in report["public_workflow_commands"]
    assert "ethos adopt" not in report["maintainer_reference_commands"]
    assert "ethos init" not in report["maintainer_reference_commands"]
    assert "ethos doctor" not in report["maintainer_reference_commands"]
    assert "ethos quality" in report["maintainer_reference_commands"]
    assert "ethos quality" in report["known_commands"]
    assert "ethos adopt" in report["known_commands"]
    assert "ethos orient" in report["known_commands"]
    assert "ethos report" in report["known_commands"]
    assert report["advanced_public_commands"] == []
    assert report["public_workflow_count"] == 5
    assert report["reader_view_count"] == 1
    assert report["scorecard_count"] == 1
    assert report["setup_count"] == 3


def test_openspec_is_governance_dependency_not_second_public_command_plane() -> None:
    report = command_registry_report()

    assert report["public_workflow_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert "ethos openspec" in report["maintainer_reference_commands"]
    assert "ethos openspec" not in report["public_workflow_commands"]
    assert "openspec validate --all --strict --json" not in report["known_commands"]
    assert report["governance_gate_commands"] == [
        "openspec validate --all --strict --json",
    ]


def test_hook_admission_is_reference_command_not_public_workflow() -> None:
    report = command_registry_report()

    assert "ethos hook" in report["maintainer_reference_commands"]
    assert "ethos hook" in report["known_commands"]
    assert "ethos hook" not in report["public_workflow_commands"]


def test_local_closeout_and_evidence_refresh_are_mechanism_commands_not_public_roots() -> None:
    report = command_registry_report()

    assert report["public_workflow_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]
    assert report["local_closeout_commands"] == [
        "ethos land --closeout --apply --authorize --expect-head <HEAD>",
    ]
    assert report["evidence_refresh_commands"] == [
        "ethos parity shadow --adopter <adopter-id> --target <repo> --execute --write-evidence",
    ]
    assert "ethos land --closeout" not in report["public_workflow_commands"]
    assert (
        "ethos parity shadow --adopter <adopter-id> --target <repo> --execute --write-evidence"
        not in report["public_workflow_commands"]
    )


def test_command_registry_scans_docs_for_retired_public_roots(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        "```bash\nproof legacy objective\n```\n",
        encoding="utf-8",
    )

    report = command_registry_report(tmp_path)

    assert report["ok"] is False
    assert report["retired_public_root_mentions"] == [
        "docs/bad.md:2:proof",
    ]
    assert report["required_gaps"] == [
        "retired_public_root_mention:docs/bad.md:2:proof",
    ]


def test_command_registry_respects_adopter_command_surface_policy(tmp_path: Path) -> None:
    (tmp_path / "rules" / "ethos").mkdir(parents=True)
    (tmp_path / "docs" / "governance").mkdir(parents=True)
    (tmp_path / "docs" / "evidence").mkdir(parents=True)
    (tmp_path / "rules" / "ethos" / "command-surface.toml").write_text(
        """
[policy]
governed_doc_globs = ["docs/governance/*.md"]
historical_exempt_roots = ["evidence"]
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "governance" / "bad.md").write_text(
        "Do not promote `proof` here.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "evidence" / "old.md").write_text(
        "Historical `proof` evidence is allowed here.\n",
        encoding="utf-8",
    )

    report = command_registry_report(tmp_path)

    assert report["ok"] is False
    assert report["retired_public_root_mentions"] == [
        "docs/governance/bad.md:1:proof",
    ]


def test_command_registry_rejects_retired_family_style_ethos_commands(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "bad.md").write_text(
        "```bash\nethos governance status\n```\n",
        encoding="utf-8",
    )

    report = command_registry_report(tmp_path)

    assert report["ok"] is False
    assert report["retired_public_command_prefix_mentions"] == [
        "docs/bad.md:2:ethos governance",
    ]
    assert report["required_gaps"] == [
        "retired_public_command_prefix_mention:docs/bad.md:2:ethos governance",
    ]


def test_current_product_docs_do_not_track_superpowers_execution_plans() -> None:
    assert not Path("docs/superpowers").exists()


def test_current_product_surfaces_do_not_expose_legacy_compatibility_terms() -> None:
    surfaces = (
        Path("packages/ethos/src/ethos/cli.py"),
        Path("packages/ethos/src/ethos/assistants/playbooks.py"),
        Path("packages/ethos-core/src/ethos_core/contracts/skill/activation.py"),
        Path("packages/ethos/src/ethos/adapters/shadow/core.py"),
        Path("system/schemas/kernel/campaign-closeout.schema.json"),
        Path("system/schemas/kernel/shadow-parity.schema.json"),
        Path("system/schemas/kernel/skill-registry.schema.json"),
        Path("system/schemas/kernel/coupling-audit.schema.json"),
    )

    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        assert "legacy" not in text.lower(), f"{path} exposes legacy compatibility"


def test_command_examples_accept_orient_as_reader_view_not_transition(
    tmp_path: Path,
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nethos orient\nethos status\nethos plan\nethos prove\nethos land\nethos publish\nethos report\n```\n",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is True
    registry = command_registry_report()
    assert "ethos orient" in registry["reader_view_commands"]
    assert "ethos orient" not in registry["public_workflow_commands"]


def test_command_examples_reject_unknown_ethos_subcommands(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nethos frobnicate --json\n```\n",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == ["unknown_ethos_command_example:README.md:2:ethos frobnicate"]


def test_command_examples_require_key_product_examples(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nethos status\nethos plan\nethos prove\n```\n",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is False
    assert "missing_command_example:ethos land" in report["required_gaps"]
    assert "missing_command_example:ethos publish" in report["required_gaps"]
    assert "missing_command_example:ethos report" in report["required_gaps"]
    assert "missing_command_example:ethos quality command-examples" not in report["required_gaps"]
    assert "missing_command_example:ethos prove --execute" not in report["required_gaps"]
