"""Markdown link, anchor, glossary, and stable-path checks for docs."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING
from urllib.parse import unquote

if TYPE_CHECKING:
    from pathlib import Path

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
GLOSSARY_TERMS = (
    "Command Plane",
    "Authority",
    "Subject",
    "Commitment",
    "Change",
    "Evidence",
    "Claim",
    "Chronicle",
)


def link_integrity_report(root: Path) -> dict[str, object]:
    """Report broken local Markdown links and anchors."""
    gaps: list[str] = []
    for path in markdown_paths(root):
        relative = path.relative_to(root).as_posix()
        if relative.startswith("evidence/"):
            continue
        for lineno, target in markdown_links(path):
            path_part, _, fragment = target.partition("#")
            if not path_part and fragment:
                target_path = path
            elif is_external_link(path_part):
                continue
            else:
                target_path = (path.parent / unquote(path_part)).resolve()
            if not target_path.exists():
                gaps.append(f"broken_link:{relative}:{lineno}:{target}")
                continue
            if fragment and target_path.suffix == ".md":
                anchors = markdown_anchors(target_path)
                if fragment not in anchors:
                    gaps.append(f"broken_anchor:{relative}:{lineno}:{target}")
    return {"ok": not gaps, "required_gaps": gaps}


def markdown_links(path: Path) -> list[tuple[int, str]]:
    """Extract Markdown links from a document."""
    links: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for match in MARKDOWN_LINK.finditer(line):
            target = match.group(1).strip()
            if not target or target.startswith("<"):
                continue
            target = target.split(None, 1)[0]
            links.append((lineno, target))
    return links


def is_external_link(target: str) -> bool:
    """Return whether a Markdown link target is external."""
    return "://" in target or target.startswith(("mailto:", "tel:"))


def markdown_anchors(path: Path) -> set[str]:
    """Return GitHub-style heading anchors for a Markdown document."""
    anchors: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        anchors.add(slugify_heading(match.group(2)))
    return anchors


def slugify_heading(text: str) -> str:
    """Return the normalized anchor slug for a Markdown heading."""
    text = re.sub(r"`([^`]+)`", r"\1", text.strip().lower())
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff _-]", "", text)
    return re.sub(r"[\s_]+", "-", text).strip("-")


def glossary_report(root: Path) -> dict[str, object]:
    """Report glossary term coverage."""
    path = root / "docs" / "reference" / "glossary.md"
    if not path.exists():
        return {"ok": False, "required_gaps": ["glossary_missing:docs/reference/glossary.md"]}
    text = path.read_text(encoding="utf-8")
    gaps = [f"glossary_term_missing:{term}" for term in GLOSSARY_TERMS if f"## {term}" not in text]
    return {"ok": not gaps, "required_gaps": gaps}


def stable_paths_report(root: Path) -> dict[str, object]:
    """Report stable docs path registration and target existence."""
    required = {
        "docs/index.md",
        "docs/start/quickstart.md",
        "docs/reference/command-plane.md",
        "docs/governance/docs-registry.md",
        "docs/reference/glossary.md",
    }
    path = root / "docs" / "_meta" / "stable_paths.toml"
    configured: set[str] = set()
    if path.exists():
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            return {"ok": False, "required_gaps": ["stable_paths_invalid_toml"]}
        configured = {
            str(item.get("path"))
            for item in payload.get("stable_path", [])
            if isinstance(item, dict) and item.get("path")
        }
    missing = sorted(f"stable_path_missing:{item}" for item in required if item not in configured)
    missing.extend(
        f"stable_path_target_missing:{item}"
        for item in sorted(configured)
        if not (root / item).exists()
    )
    return {"ok": not missing, "required_gaps": missing, "configured": sorted(configured)}


def markdown_paths(root: Path) -> tuple[Path, ...]:
    """Return Markdown paths covered by docs quality checks."""
    paths = [root / "README.md", root / "CONTRIBUTING.md", root / "CHANGELOG.md"]
    paths.extend(sorted((root / "docs").rglob("*.md")))
    paths.extend(sorted((root / "evidence").rglob("*.md")))
    return tuple(path for path in paths if path.exists())
