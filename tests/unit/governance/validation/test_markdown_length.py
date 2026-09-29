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
