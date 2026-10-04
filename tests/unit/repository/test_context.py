"""Installed agent guidance is a projection of the selected product."""

import hashlib
from pathlib import Path

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
    assert {source["role"] for source in sources} == {"product-meaning", "rules"}
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
    package = tmp_path / "package"
    guidance = package / "data/skills/ethos-repository-work/SKILL.md"
    guidance.parent.mkdir(parents=True)
    guidance.write_text("Use ethos status.\n", encoding="utf-8")
    for relative in ("docs/governance/product-design-contract.md", "rules/README.md"):
        target = package / "data/governance" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((Path(__file__).resolve().parents[3] / relative).read_bytes())
    (package / "subdirectory").mkdir()
    monkeypatch.setattr(context_owner, "files", lambda _name: package / "subdirectory/..")

    context = repository_context(tmp_path)["agent_guidance"]
    assert isinstance(context, dict)
    observed = context["path"]
    assert observed == guidance.resolve().as_posix()
    sources = context["sources"]
    assert all(Path(source["path"]).is_relative_to(package) for source in sources)
    assert all(source["origin"] == "product" for source in sources)
