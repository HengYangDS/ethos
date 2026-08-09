from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.boundary.product as product

if TYPE_CHECKING:
    from pathlib import Path


def test_release_history_filter_rejects_state_cache_and_skipped_directories(
    tmp_path: Path,
) -> None:
    state = tmp_path / ".ethos/state/record.md"
    skipped = tmp_path / "docs/history/node_modules/record.md"
    state.parent.mkdir(parents=True)
    skipped.parent.mkdir(parents=True)
    state.write_text("state\n", encoding="utf-8")
    skipped.write_text("skipped\n", encoding="utf-8")

    assert not product._is_text_release_visible_historical_file(  # noqa: SLF001
        state, root=tmp_path
    )
    assert not product._is_text_release_visible_historical_file(  # noqa: SLF001
        skipped, root=tmp_path
    )


def test_release_history_accepts_a_declared_single_file_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "history.md"
    path.write_text("history\n", encoding="utf-8")
    monkeypatch.setattr(product, "RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES", ("history.md",))

    assert product.release_visible_historical_files(tmp_path) == [path]


def test_line_findings_ignore_non_utf8_product_content(tmp_path: Path) -> None:
    path = tmp_path / "record.md"
    path.write_bytes(b"\xff")

    assert (
        product._line_findings(  # noqa: SLF001
            path, "record.md", (("local", product.LOCAL_PATH_PATTERNS[0]),)
        )
        == []
    )


@pytest.mark.parametrize(
    ("function", "payload"),
    [
        (product._json_package_metadata_findings, []),  # noqa: SLF001
        (product._toml_package_metadata_findings, {"project": []}),  # noqa: SLF001
        (product._npm_distribution_manifest_findings, []),  # noqa: SLF001
    ],
)
def test_package_metadata_non_object_roots_do_not_mint_findings(
    tmp_path: Path, function: object, payload: object
) -> None:
    path = tmp_path / ("package.json" if payload == [] else "pyproject.toml")
    text = json.dumps(payload) if path.suffix == ".json" else "project = []\n"
    path.write_text(text, encoding="utf-8")

    assert function(path, path.name) == []  # type: ignore[operator]


def test_identity_entries_skip_non_object_rows_and_report_personal_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = product._identity_entries(  # noqa: SLF001
        {
            "allowed_identities": [
                "invalid",
                {"role": "maintainer", "name": "Private Person", "email": "person@example.com"},
            ]
        }
    )
    monkeypatch.setattr(
        product,
        "PERSONAL_PATTERNS",
        (re.compile(r"Private Person"),),
    )

    findings = product._identity_entry_findings(  # noqa: SLF001
        entries=entries, policy_path=".ethos/workspace.toml"
    )

    assert entries == [
        {"role": "maintainer", "name": "Private Person", "email": "person@example.com"}
    ]
    assert [finding.kind for finding in findings] == ["personal_identity_literal"]


def test_missing_workspace_policy_has_deterministic_fail_closed_report(tmp_path: Path) -> None:
    assert product.load_workspace_commit_policy(tmp_path) == {}

    report = product.contributor_policy_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["summary"] == {
        "identity_mode": "",
        "identity_count": 0,
        "roles": [],
        "finding_count": 2,
    }
