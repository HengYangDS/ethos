"""Installed agent guidance is a projection of the selected product."""

import hashlib
from pathlib import Path

import ethos.repository.context as context_owner
from ethos.repository.context import repository_context


def test_repository_context_exposes_portable_installed_guidance(tmp_path: Path) -> None:
    """Agents discover guidance without an ETHOS checkout or vendor-specific host."""
    context = repository_context(tmp_path)
    guidance = context["agent_guidance"]
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


def test_repository_context_canonicalizes_the_installed_guidance_path(
    monkeypatch, tmp_path: Path
) -> None:
    """SDK and subprocess status agree despite an editable-install dot-segment path."""
    package = tmp_path / "package"
    guidance = package / "data/skills/ethos-repository-work/SKILL.md"
    guidance.parent.mkdir(parents=True)
    guidance.write_text("Use ethos status.\n", encoding="utf-8")
    (package / "subdirectory").mkdir()
    monkeypatch.setattr(context_owner, "files", lambda _name: package / "subdirectory/..")

    observed = repository_context(tmp_path)["agent_guidance"]["path"]
    assert observed == guidance.resolve().as_posix()
