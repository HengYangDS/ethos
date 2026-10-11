"""Current Markdown length observes source ownership instead of file suffix alone."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("relative", "state", "count"),
    [
        ("docs/topic.md", "canonical", 512),
        ("docs/topic.md", "canonical", 513),
        ("docs/topic.md", "archived", 513),
        ("README.md", "canonical", 513),
        ("handbook/topic.md", "canonical", 513),
    ],
)
def test_current_markdown_uses_physical_nonblank_limit(
    tmp_path: Path, relative: str, state: str, count: int
) -> None:
    """Blank lines and metadata relabeling cannot evade the portable limit."""
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    base = (
        f"---\nsubject: sample:topic\nrole: reference\nstate: {state}\nrelations: {{}}\n"
        "---\n\n# Topic\n\nPurpose: exercise length.\n"
        if relative.startswith("docs/")
        else "# Topic\n"
    )
    path.write_text(base + "record\n\n" * (count - sum(bool(x.strip()) for x in base.splitlines())))
    git(root, "add", "--", relative)

    report = docs_registry_report(root)

    expected = [] if count == 512 else [f"docs_length_exceeded:{relative}:{count}>512"]
    assert report["required_gaps"] == expected
    assert report["verdict"] == ("pass" if count == 512 else "block")


def test_release_history_is_not_bounded_by_document_length(tmp_path: Path) -> None:
    """Neither total history nor one release entry is a current document topic."""
    root = init_git_repo(tmp_path / "repo")
    history = "# Changelog\n\n## [Unreleased]\n\n- Pending.\n"
    history += "".join(
        f"\n## [{version}.0.0] - 2026-09-29\n" + "- Change.\n" * 600 for version in range(2, 0, -1)
    )
    assert sum(bool(line.strip()) for line in history.splitlines()) > 512
    (root / "CHANGELOG.md").write_text(history)
    commit_fixture(root, "sectioned release history")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    provider = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]

    assert result.returncode == 0
    assert report["verdict"] == "pass"
    assert provider["required_gaps"] == []


@pytest.mark.parametrize(
    ("relative", "expected"),
    [
        ("CHANGELOG.md", []),
        ("handbook/CHANGELOG.md", ["docs_length_exceeded:handbook/CHANGELOG.md:513>512"]),
    ],
)
def test_only_release_owned_changelog_is_exempt_from_document_length(
    tmp_path: Path, relative: str, expected: list[str]
) -> None:
    """A filename elsewhere does not turn authored prose into release history."""
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Changelog\n" + "- Undifferentiated.\n" * 512)
    git(root, "add", "--", relative)

    report = docs_registry_report(root)

    assert report["required_gaps"] == expected


def test_release_history_still_requires_readable_source(tmp_path: Path) -> None:
    """The length exemption does not make an unreadable release carrier healthy."""
    root = init_git_repo(tmp_path / "repo")
    (root / "CHANGELOG.md").write_bytes(b"\xff")
    git(root, "add", "CHANGELOG.md")

    report = docs_registry_report(root)

    assert report["required_gaps"] == ["docs_source_unavailable:CHANGELOG.md"]


def test_official_and_owned_generated_markdown_are_not_authored_docs(tmp_path: Path) -> None:
    """The document limit never mistakes official intent or owned output for prose."""
    root = init_git_repo(tmp_path / "repo")
    declaration = root / ".config/checks/ci/templates.toml"
    declaration.parent.mkdir(parents=True)
    declaration.write_text(
        'schema = "ethos-ci-template-consistency-v1"\n'
        '[[projection]]\nkind = "copy"\ntemplate = "source.txt"\n'
        'projection = "docs/generated.md"\n'
    )
    (root / "source.txt").write_text("content\n" * 513)
    for relative in (
        "docs/generated.md",
        "openspec/specs/quality/spec.md",
        "openspec/changes/change/design.md",
        "openspec/changes/archive/2026-08-01-old/design.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n" * 513)
    git(root, "add", "--", ".config/checks/ci/templates.toml", "source.txt", "docs", "openspec")

    report = docs_registry_report(root)

    assert report["verdict"] == "pass", report["required_gaps"]


@pytest.mark.parametrize("nonblank_lines", [512, 513])
def test_public_docs_gate_enforces_current_boundary(tmp_path: Path, nonblank_lines: int) -> None:
    """The real prove entrypoint preserves exact acceptance and failed-document observations."""
    root = init_git_repo(tmp_path / "repo")
    (root / "README.md").write_text("# Probe\n" + "record\n" * (nonblank_lines - 1))
    commit_fixture(root, "document boundary")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    checks = report["data"]["checks"]
    provider = json.loads(checks[0]["stdout"])["providers"][0]["report"]
    exceeded = nonblank_lines > 512

    assert (result.returncode != 0) is exceeded
    assert report["verdict"] == ("block" if exceeded else "pass")
    assert report["summary"]["proof_attestation_issued"] is False
    assert provider["required_gaps"] == (
        [f"docs_length_exceeded:README.md:{nonblank_lines}>512"] if exceeded else []
    )
