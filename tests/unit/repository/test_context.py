"""Installed agent guidance is a projection of the selected product."""

import hashlib
import shutil
import tomllib
from pathlib import Path

import pytest

import ethos.repository.context as context_owner
from ethos.repository.context import repository_context
from ethos.repository.policy.references.markdown import markdown_tokens


def test_repository_context_exposes_portable_installed_guidance(tmp_path: Path) -> None:
    """Agents discover guidance without an ETHOS checkout or vendor-specific host."""
    context = repository_context(tmp_path)
    guidance = context["agent_guidance"]
    assert isinstance(guidance, dict)
    packaged = Path(guidance["path"])

    assert guidance["media_type"] == "text/markdown"
    assert guidance["authority"] == "product_projection"
    assert packaged.is_file()
    content = packaged.read_text(encoding="utf-8")
    assert guidance["sha256"] == hashlib.sha256(content.encode()).hexdigest()
    assert "ethos status" in content
    assert "next_action" in content
    assert "uv run" not in content
    assert "/Users/" not in content
    sources = guidance["sources"]
    assert {source["role"] for source in sources} == {
        "product-meaning",
        "rules",
        "agent-method",
        "documentation",
        "adoption",
        "release",
        "recovery",
        "commands",
    }
    assert all(source["origin"] == "product" for source in sources)
    assert all(
        source["sha256"] == hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest()
        for source in sources
    )
    for source in sources:
        tokens = markdown_tokens(Path(source["path"]).read_text(encoding="utf-8"))
        assert tokens is not None
        headings = {
            tokens[index + 1].content
            for index, token in enumerate(tokens)
            if token.type == "heading_open"
        }
        assert set(source["sections"]) <= headings
    assert "agent_guidance.sources" in content


def test_repository_context_canonicalizes_the_installed_guidance_path(
    monkeypatch, tmp_path: Path
) -> None:
    """SDK and subprocess status agree despite an editable-install dot-segment path."""
    package = _installed_package(tmp_path)
    guidance = package / "data/skills/ethos-repository-work/SKILL.md"
    (package / "subdirectory").mkdir()
    monkeypatch.setattr(context_owner, "files", lambda _name: package / "subdirectory/..")

    context = repository_context(tmp_path)["agent_guidance"]
    assert isinstance(context, dict)
    observed = context["path"]
    assert observed == guidance.resolve().as_posix()
    sources = context["sources"]
    assert all(Path(source["path"]).is_relative_to(package) for source in sources)
    assert all(source["origin"] == "product" for source in sources)


def test_installed_context_exposes_the_documentation_owner_without_source_checkout(
    monkeypatch, tmp_path: Path
) -> None:
    """An adopter can open the selected docs contract from package-owned bytes."""
    package = _installed_package(tmp_path)
    monkeypatch.setattr(context_owner, "files", lambda _name: package)

    context = repository_context(tmp_path)
    guidance = context["agent_guidance"]
    assert isinstance(guidance, dict)
    documentation = next(
        source for source in guidance["sources"] if source["role"] == "documentation"
    )
    path = Path(documentation["path"])
    assert path.is_relative_to(package)
    assert path.is_file()
    assert documentation["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    path.unlink()
    with pytest.raises(FileNotFoundError):
        repository_context(tmp_path)


def _installed_package(tmp_path: Path) -> Path:
    """Stage resources from the native package declaration, not another source map."""
    root = Path(__file__).resolve().parents[3]
    package = tmp_path / "package"
    guide = package / "data/skills/ethos-repository-work/SKILL.md"
    guide.parent.mkdir(parents=True)
    shutil.copyfile(root / "src/ethos/data/skills/ethos-repository-work/SKILL.md", guide)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    for source, target in project["tool"]["hatch"]["build"]["targets"]["wheel"][
        "force-include"
    ].items():
        if not target.startswith("ethos/data/governance/"):
            continue
        destination = package / target.removeprefix("ethos/")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if (root / source).is_dir():
            shutil.copytree(root / source, destination)
        else:
            shutil.copyfile(root / source, destination)
    return package
