from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.boundary.product import release_visible_historical_files

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_release_history_public_inventory_rejects_state_cache_and_skipped_directories(
    tmp_path: Path,
) -> None:
    visible = tmp_path / "docs/history/record.md"
    state = tmp_path / ".ethos/state/record.md"
    skipped = tmp_path / "docs/history/node_modules/record.md"
    for path in (visible, state, skipped):
        _write(path, "record\n")

    assert release_visible_historical_files(tmp_path) == [visible]


def test_product_boundary_public_report_ignores_non_utf8_and_non_object_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_bytes(b"\xff")
    _write(tmp_path / "package.json", "[]")
    _write(tmp_path / "pyproject.toml", "project = []\n")
    _write(tmp_path / "distributions/npm/package.json", "[]")

    report = product_boundary_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["findings"] == []
    assert report["summary"]["scanned_file_count"] == 4


def test_contributor_policy_public_report_skips_non_object_rows_and_reports_identity(
    tmp_path: Path,
) -> None:
    private_email = "named" + "@" + "private.example"
    _write(
        tmp_path / ".ethos/workspace.toml",
        f"""[commit_policy]
identity_mode = "external"

[[commit_policy.allowed_identities]]
role = "maintainer"
name = "Named Person"
email = "{private_email}"

[[commit_policy.allowed_identities]]
role = "bot"
name = "Automation Service"
email = "automation@example.com"
""",
    )
    payload = json.loads(json.dumps(contributor_policy_report(tmp_path)))

    assert payload["verdict"] == "block"
    assert [finding["kind"] for finding in payload["findings"]] == ["personal_identity_literal"]
    assert payload["summary"]["identity_count"] == 2


def test_contributor_policy_public_report_skips_non_object_identity_rows(tmp_path: Path) -> None:
    _write(
        tmp_path / ".ethos/workspace.toml",
        """[commit_policy]
identity_mode = "external"
allowed_identities = ["invalid-row"]
""",
    )

    report = contributor_policy_report(tmp_path)

    assert report["summary"]["identity_count"] == 0
    assert report["allowed_identities"] == []
    assert "allowed_identities_missing:.ethos/workspace.toml:1" in report["required_gaps"]


def test_missing_workspace_policy_has_deterministic_fail_closed_report(tmp_path: Path) -> None:
    report = contributor_policy_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["summary"] == {
        "identity_mode": "",
        "identity_count": 0,
        "roles": [],
        "finding_count": 2,
    }
    assert set(report["required_gaps"]) == {
        "identity_mode_missing:.ethos/workspace.toml:1",
        "allowed_identities_missing:.ethos/workspace.toml:1",
    }
