"""Portable decision rationale under the existing Docs Registry contract."""

from __future__ import annotations

import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.policy.references.commands import command_invocation
from ethos.repository.policy.references.markdown import markdown_tokens

if TYPE_CHECKING:
    from collections.abc import Iterator

    from markdown_it.token import Token

DECISION_RECORD_NAME = re.compile(r"^dr-([0-9]{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
DECISION_SECTIONS = (
    "Context",
    "Decision",
    "Alternatives Rejected",
    "Consequences and Boundary",
    "Evidence and Revisit",
)


def decision_record_gaps(root: Path, registry: list[dict[str, Any]]) -> list[str]:
    """Validate one shared identity, disposition, rationale and carrier boundary."""
    ids: dict[str, list[str]] = {}
    gaps: list[str] = []
    for entry in registry:
        if entry.get("role") != "decision":
            continue
        relative = str(entry["path"])
        match = DECISION_RECORD_NAME.fullmatch(PurePosixPath(relative).name)
        if match is None or match[1] == "0000":
            gaps.append(f"docs_decision_name_invalid:{relative}")
            continue
        ids.setdefault(match[1], []).append(relative)
        expected = f"DR-{match[1]}"
        if entry.get("decision_id") != expected:
            gaps.append(f"docs_decision_identity_mismatch:{relative}")
        if entry.get("decision_status") != "accepted" or entry.get("state") != "canonical":
            gaps.append(f"docs_decision_status_invalid:{relative}")
        gaps.extend(_rationale_gaps(root / relative, relative, expected))
    gaps.extend(
        f"docs_decision_id_duplicate:{number}:{','.join(sorted(paths))}"
        for number, paths in sorted(ids.items())
        if len(paths) > 1
    )
    return gaps


def _rationale_gaps(path: Path, relative: str, identity: str) -> list[str]:
    source = path.read_text(encoding="utf-8")
    commented = source.startswith("<!--\n---\n")
    body = source.split("\n---\n", 1)[1] if source.startswith("---\n") else source
    parsed = markdown_tokens(body)
    if parsed is None:
        return [f"docs_decision_source_unavailable:{relative}"]
    tokens = parsed[1:] if commented and parsed and parsed[0].type == "html_block" else parsed
    headings = [(i, t) for i, t in enumerate(tokens) if t.type == "heading_open"]
    titles = [(i, t) for i, t in headings if t.tag == "h1"]
    gaps: list[str] = []
    if (
        len(titles) != 1
        or titles[0][1].level != 0
        or not tokens[titles[0][0] + 1].content.startswith(identity + ": ")
        or not tokens[titles[0][0] + 1].content[len(identity) + 2 :].strip()
    ):
        gaps.append(f"docs_decision_title_mismatch:{relative}")
    sections = [(i, t) for i, t in headings if t.tag != "h1"]
    if (
        any(t.tag != "h2" or t.level != 0 for _, t in sections)
        or tuple(tokens[i + 1].content for i, _ in sections) != DECISION_SECTIONS
    ):
        gaps.append(f"docs_decision_sections_invalid:{relative}")
    else:
        for number, (start, _) in enumerate(sections):
            stop = sections[number + 1][0] if number + 1 < len(sections) else len(tokens)
            if not _authored_rationale(tokens[start + 3 : stop]):
                gaps.append(
                    f"docs_decision_rationale_missing:{relative}:{DECISION_SECTIONS[number]}"
                )
    if violation := _execution_violation(tokens):
        gaps.append(f"docs_decision_execution_content:{relative}:{violation}")
    return gaps


def _authored_rationale(tokens: tuple[Token, ...]) -> bool:
    """Distinguish authored rationale from supporting quotations in one section."""
    quoted = 0
    for token in tokens:
        if token.type == "blockquote_open":
            quoted += 1
        elif token.type == "blockquote_close":
            quoted -= 1
        elif token.type == "inline" and not quoted:
            text = "".join(
                child.content
                for child in token.children or ()
                if child.type in {"text", "code_inline"}
            )
            if text.strip():
                return True
    return False


def _execution_violation(tokens: tuple[Token, ...]) -> str:
    for token in tokens:
        if token.type in {"fence", "code_block", "html_block"}:
            return token.type
        if token.type != "inline":
            continue
        if re.match(r"^\[[ xX]\](?:\s|$)", token.content) and token.level > 0:
            return "task"
        if any(child.type == "html_inline" for child in token.children or ()):
            return "html_inline"
        if any(
            child.type == "code_inline" and command_invocation(child.content) is not False
            for child in _rationale_children(token)
        ):
            return "inline_invocation"
        for line in _prose_without_references(token).splitlines():
            if command_invocation(line) is True:
                return "invocation"
    return ""


def _rationale_children(token: Token) -> Iterator[Token]:
    """Keep reference labels under their Markdown link, not invocation inspection."""
    link_depth = 0
    for child in token.children or ():
        if child.type == "link_open":
            link_depth += 1
        elif child.type == "link_close":
            link_depth -= 1
        elif not link_depth:
            yield child


def _prose_without_references(token: Token) -> str:
    prose: list[str] = []
    for child in _rationale_children(token):
        if child.type == "text":
            prose.append(child.content)
        elif child.type == "softbreak":
            prose.append(" ")
        elif child.type == "hardbreak":
            prose.append("\n")
    return "".join(prose)
