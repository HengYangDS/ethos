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
        ("docs/topic.md", "canonical", 500),
        ("docs/topic.md", "canonical", 501),
        ("docs/topic.md", "archived", 501),
        ("README.md", "canonical", 501),
        ("handbook/topic.md", "canonical", 501),
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

    expected = [] if count == 500 else [f"docs_length_exceeded:{relative}:501>500"]
    assert report["required_gaps"] == expected
    assert report["verdict"] == ("pass" if count == 500 else "block")


def test_release_history_is_bounded_by_navigable_version_section(tmp_path: Path) -> None:
    """An append-only changelog is not one current reader topic."""
    root = init_git_repo(tmp_path / "repo")
    history = "# Changelog\n\n## [Unreleased]\n\n- Pending.\n"
    history += "".join(
        f"\n## [{version}.0.0] - 2026-09-29\n" + "- Change.\n" * 100 for version in range(6, 0, -1)
    )
    assert sum(bool(line.strip()) for line in history.splitlines()) > 500
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
    ("body", "count"),
    [
        ("# Changelog\n" + "- Undifferentiated.\n" * 500, 501),
        (
            "# Changelog\n## [Unreleased]\n- Pending.\n"
            "## [1.0.0] - 2026-09-29\n" + "- Change.\n" * 500,
            501,
        ),
        (
            "# Changelog\n## [Unreleased]\n```\n## [1.0.0] - 2026-09-29\n```\n" + "- Note.\n" * 496,
            501,
        ),
    ],
    ids=("undifferentiated", "oversized-release", "fenced-heading"),
)
def test_changelog_name_does_not_exempt_unbounded_content(
    tmp_path: Path, body: str, count: int
) -> None:
    """Missing version structure and overlong individual releases still block."""
    root = init_git_repo(tmp_path / "repo")
    (root / "CHANGELOG.md").write_text(body)
    git(root, "add", "CHANGELOG.md")

    report = docs_registry_report(root)

    assert report["required_gaps"] == [f"docs_length_exceeded:CHANGELOG.md:{count}>500"]


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
    (root / "source.txt").write_text("content\n" * 501)
    for relative in (
        "docs/generated.md",
        "openspec/specs/quality/spec.md",
        "openspec/changes/change/design.md",
        "openspec/changes/archive/2026-08-01-old/design.md",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content\n" * 501)
    git(root, "add", "--", ".config/checks/ci/templates.toml", "source.txt", "docs", "openspec")

    report = docs_registry_report(root)

    assert report["verdict"] == "pass", report["required_gaps"]


def test_public_docs_gate_rejects_501_nonblank_lines(tmp_path: Path) -> None:
    """The real prove entrypoint carries the precise failed-document observation."""
    root = init_git_repo(tmp_path / "repo")
    (root / "README.md").write_text("# Probe\n" + "record\n" * 500)
    commit_fixture(root, "long document")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    checks = report["data"]["checks"]
    provider = json.loads(checks[0]["stdout"])["providers"][0]["report"]

    assert result.returncode != 0
    assert report["verdict"] == "block"
    assert report["summary"]["proof_attestation_issued"] is False
    assert provider["required_gaps"] == ["docs_length_exceeded:README.md:501>500"]
