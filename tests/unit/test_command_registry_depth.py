from __future__ import annotations

from pathlib import Path

from ethos_governance.command_registry import command_registry_report


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
