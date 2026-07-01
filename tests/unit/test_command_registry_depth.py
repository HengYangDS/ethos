from __future__ import annotations

from pathlib import Path

from ethos_repository.command_registry import command_registry_report
from ethos_repository.docs_registry import command_examples_report


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
    (tmp_path / "docs" / "current").mkdir(parents=True)
    (tmp_path / "docs" / "evidence").mkdir(parents=True)
    (tmp_path / "rules" / "ethos" / "command-surface.toml").write_text(
        """
[policy]
current_doc_globs = ["docs/current/*.md"]
historical_exempt_roots = ["docs/evidence"]
""".lstrip(),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "current" / "bad.md").write_text(
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
        "docs/current/bad.md:1:proof",
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


def test_command_examples_reject_unknown_ethos_subcommands(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nethos frobnicate --json\n```\n",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "unknown_ethos_command_example:README.md:2:ethos frobnicate"
    ]


def test_command_examples_require_key_product_examples(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nethos status\nethos plan\nethos prove\n```\n",
        encoding="utf-8",
    )

    report = command_examples_report(tmp_path)

    assert report["ok"] is False
    assert "missing_command_example:ethos quality command-examples" in report["required_gaps"]
    assert "missing_command_example:ethos prove --execute" in report["required_gaps"]
