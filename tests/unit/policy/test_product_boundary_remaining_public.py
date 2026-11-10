"""Observe release history and metadata without inventing findings for unreadable data."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.boundary.product import release_visible_historical_files
from tests.support.governed_repository import write_file
from tests.support.private_addresses import DOCUMENTATION_FORGE
from tests.support.private_addresses import INTERNAL_FORGE
from tests.support.private_addresses import PRIVATE_FORGE
from tests.support.private_addresses import ipv4

if TYPE_CHECKING:
    from pathlib import Path


def test_release_history_public_inventory_skips_dependency_directories(tmp_path: Path) -> None:
    visible = tmp_path / "docs/history/record.md"
    skipped = tmp_path / "docs/history/node_modules/record.md"
    for path in (visible, skipped):
        write_file(path, "record\n")

    assert release_visible_historical_files(tmp_path) == [visible]


def test_product_boundary_public_report_ignores_non_utf8_and_non_object_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_bytes(b"\xff")
    write_file(tmp_path / "package.json", "[]")
    write_file(tmp_path / "pyproject.toml", "project = []\n")

    report = product_boundary_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["findings"] == []
    assert report["summary"]["scanned_file_count"] == 3


# ETHOS's own surfaces keep refusing loopback and link-local literals in every form; joined here.
LOOPBACK_AND_LINK_LOCAL_IDS = ["loopback", "link-local", "link-local-v6", "loopback-v6", "ssh-user"]


LOOPBACK_AND_LINK_LOCAL = [
    '("' + ipv4(127, 0, 0, 1) + '", 0)',
    "addr=" + ipv4(169, 254, 1, 1),
    "fe" + "80::1%en0",
    "http://[" + ":" + ":1]:9/",
    "ssh://deploy@" + ipv4(127, 0, 0, 1) + "/repo",
]


@pytest.mark.parametrize(
    ("line", "found"),
    [
        (f"forge: http://{INTERNAL_FORGE}/team/repo", True),
        (f"bind {PRIVATE_FORGE}", True),
        ("api: http://" + "localhost:8080/v1", True),
        (f"forge: http://{DOCUMENTATION_FORGE}/team/repo at forge.example.invalid", False),
        ("bind ('localhost', 0)", False),
        *((text, True) for text in LOOPBACK_AND_LINK_LOCAL),
    ],
    ids=[
        "internal-name",
        "private-literal",
        "localhost-url",
        "documentation",
        "localhost-name",
        *LOOPBACK_AND_LINK_LOCAL_IDS,
    ],
)
def test_product_surfaces_refuse_the_paradigm_address_classes(
    tmp_path: Path, line: str, *, found: bool
) -> None:
    """The boundary takes address classes from the paradigm and keeps refusing localhost URLs."""
    write_file(tmp_path / "README.md", line + "\n")

    report = product_boundary_report(tmp_path)

    kinds = {finding["kind"] for finding in report["findings"]}
    assert kinds == ({"private_infrastructure_literal"} if found else set())
