"""Declared normative responsibilities require actual portable reader routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.git import run_git
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.documentation import documentation_fixture

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("docs", ["docs", "handbook"])
@pytest.mark.parametrize("route", ["inline", "reference", "indirect"])
def test_docs_health_requires_reachable_declared_normative_sources(
    tmp_path: Path, docs: str, route: str
) -> None:
    """An unrelated child link cannot hide unreachable normative responsibilities."""
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        f"profile_id = 'sample'\nnormative_sources = ['{docs}/topics/contract.md', "
        f"'{docs}/other.md', 'rules/core.md']\n[roots]\ndocs = '{docs}'\n"
    )
    handbook = tmp_path / docs
    topics = handbook / "topics"
    topics.mkdir(parents=True)
    (topics / "contract.md").write_text(
        documentation_fixture("sample:contract", "policy", "canonical", "Contract")
        + "\nRead [Other](../other.md).\n"
    )
    (topics / "README.md").write_text(
        documentation_fixture("sample:topics", "index", "canonical", "Topics")
        + "\nRead [Contract](contract.md).\n"
    )
    for name in ("other", "note"):
        (handbook / f"{name}.md").write_text(
            documentation_fixture(f"sample:{name}", "policy", "canonical", name.title())
        )
    entry = handbook / "README.md"
    original = documentation_fixture("sample:docs", "index", "canonical", "Handbook")
    entry.write_text(original + "\nRead [Note](note.md).\n")
    assert docs_health_report(tmp_path)["readme_disposition"] == [
        f"docs_normative_source_unreachable:{docs}/other.md",
        f"docs_normative_source_unreachable:{docs}/topics/contract.md",
    ]
    destination = "topics/" if route == "indirect" else "topics/contract.md"
    navigation = (
        f"\nRead [Contract][contract].\n\n[contract]: {destination}\n"
        if route == "reference"
        else f"\nRead [Contract]({destination}).\n"
    )
    entry.write_text(original + navigation)
    assert docs_health_report(tmp_path)["readme_disposition"] == []
    assert not (tmp_path / "rules/core.md").exists()


@pytest.mark.parametrize("docs", ["docs", "handbook"])
def test_docs_registry_binds_normative_routes_to_selected_source(tmp_path: Path, docs: str) -> None:
    """Ignored disk bytes cannot satisfy a source obligation; forced tracking can."""
    run_git(tmp_path, "init", "--quiet")
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        f"profile_id = 'sample'\nnormative_sources = ['{docs}/contract.md']\n"
        f"[roots]\ndocs = '{docs}'\n"
    )
    handbook = tmp_path / docs
    handbook.mkdir()
    (tmp_path / ".gitignore").write_text(f"{docs}/contract.md\n")
    (handbook / "README.md").write_text(
        documentation_fixture("sample:docs", "index", "canonical", "Handbook")
        + "\nRead [Note](note.md) and [Contract](contract.md).\n"
    )
    (handbook / "note.md").write_text(
        documentation_fixture("sample:note", "policy", "canonical", "Note")
    )
    contract = handbook / "contract.md"
    contract.write_text(documentation_fixture("sample:contract", "policy", "canonical", "Contract"))
    run_git(tmp_path, "add", ".gitignore", ".ethos/profile.toml", docs)
    originals = {path: path.read_bytes() for path in handbook.glob("*.md")}

    report = docs_registry_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["document_count"] == 2
    assert report["readme_disposition"] == [f"docs_normative_source_unreachable:{docs}/contract.md"]
    registry = report["registry"]
    assert isinstance(registry, list)
    assert {entry["path"] for entry in registry} == {
        f"{docs}/README.md",
        f"{docs}/note.md",
    }
    assert build_docs_registry(tmp_path, selected_documents=()) == []
    assert docs_health_report(tmp_path, tracked_documents=())["document_count"] == 0
    assert (
        docs_health_report(tmp_path, tracked_documents=(".ethos/profile.toml",))["document_count"]
        == 0
    )
    assert all(path.read_bytes() == original for path, original in originals.items())

    run_git(tmp_path, "add", "--force", f"{docs}/contract.md")
    report = docs_registry_report(tmp_path)
    assert report["verdict"] == "pass"
    assert report["document_count"] == 3
    assert {
        entry["path"]
        for entry in build_docs_registry(
            tmp_path, selected_documents=tuple(git_files(tmp_path, "*.md"))
        )
    } == {f"{docs}/{name}.md" for name in ("README", "note", "contract")}
    contract.unlink()
    assert docs_registry_report(tmp_path)["required_gaps"] == [
        f"docs_source_unavailable:{docs}/contract.md"
    ]


def test_docs_registry_preserves_selected_source_confinement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selected symbolic alias cannot borrow authority from excluded disk bytes."""
    root = tmp_path / "repo"
    root.mkdir()
    run_git(root, "init", "--quiet")
    documentation = root / "docs"
    documentation.mkdir()
    original = tmp_path / "outside.md"
    original.write_text(documentation_fixture("sample:contract", "policy", "canonical", "Contract"))
    alias = documentation / "contract.md"
    try:
        alias.symlink_to(original)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic link creation is unavailable")
    run_git(root, "add", "docs/contract.md")
    reads: list[Path] = []
    original_read = type(original).read_text

    def recorded_read(path: Path, *args, **kwargs) -> str:
        reads.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(type(original), "read_text", recorded_read)
    with pytest.raises(ValueError, match=r"docs_source_unavailable:docs/contract\.md"):
        build_docs_registry(root, selected_documents=("docs/contract.md",))
    assert docs_registry_report(root)["required_gaps"] == [
        "docs_source_unavailable:docs/contract.md"
    ]
    assert alias not in reads
    assert original not in reads
    assert original.read_text().startswith("---\nsubject: sample:contract\n")
