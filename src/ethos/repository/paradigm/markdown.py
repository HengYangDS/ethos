"""Markdown layout of the repository paradigm.

Markdown spacing follows the parsed CommonMark structure, as the shared Markdown
formatter lays it out. One blank line separates adjacent blocks and follows front
matter, consecutive reference definitions stay together, and no blank line repeats or
pads a document's edges. A list item of one block, or of blocks without a blank line
between them, stays tight with the next item; an item whose blocks a blank line
separates keeps one blank line between its blocks and before the next item. The
formatter keeps a blank line that an author leaves after a one-block item, so the
paradigm reports it. Literal blocks, quotes and the node after a formatter-ignore
comment keep their bytes.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING
from typing import NamedTuple

from markdown_it import MarkdownIt

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_PARSER = MarkdownIt("commonmark").enable("table")
_FRONT_MATTER = "---"
_IGNORE = "<!-- prettier-ignore -->"
_LISTS = frozenset({"bullet_list_open", "ordered_list_open"})
_OPAQUE = frozenset({"blockquote_open", "table_open"})
_LITERAL = frozenset({"inline", "fence", "code_block", "html_block"})
_JOINED = frozenset({0})
_SEPARATED = frozenset({1})
_EITHER = frozenset({0, 1})


class MarkdownLayout(NamedTuple):
    """A document's layout and the separators it changes.

    The text is None when laying the document out would change its structure; each changed
    line is the 1-based line that follows a separator the layout changes.
    """

    text: str | None
    changed: tuple[int, ...]


class _Block(NamedTuple):
    """One block by its first and last non-blank line, kind and child blocks."""

    first: int
    last: int
    kind: str
    children: list[_Block]
    ignores_next: bool = False


class _Separator(NamedTuple):
    """The blank lines [start, end) between two blocks and the counts the layout admits."""

    start: int
    end: int
    admitted: frozenset[int]


def markdown_layout_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str], received: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report each authored Markdown document whose blank lines differ from its structure."""
    for path in sorted(tracked - received):
        if not path.endswith(".md") or path.startswith(paradigm.immutable_roots):
            continue
        changed = markdown_layout(tracked_text(root, path, tracked) or "").changed
        if changed:
            count = f"{len(changed)} separator{'s' if len(changed) > 1 else ''}"
            yield ParadigmGap(
                "markdown-layout",
                path,
                f"separate the blocks of {path} with one blank line, keep one-block list items "
                f"tight and drop edge padding ({count}, first at line {changed[0]}); "
                "ethos lane repair-paradigm --apply lays it out",
            )


def markdown_layout_repair(
    _paradigm: RepositoryParadigm, _gap: ParadigmGap, text: str | None
) -> tuple[str, str] | None:
    """Lay a document out by its parsed structure, unless that would change the structure."""
    layout = markdown_layout(text or "")
    if layout.text is None or layout.text == (text or ""):
        return None
    return layout.text, ""


def markdown_layout(text: str) -> MarkdownLayout:
    """Lay one document out by its parsed structure and name the lines it changes."""
    lines = text.split("\n")
    content = [index for index, line in enumerate(lines) if line.strip()]
    if not content:
        return MarkdownLayout("", (1,) if text else ())
    first, last = content[0], content[-1]
    body = lines[first : last + 1]
    edits = [
        separator
        for separator in _separators(body, front_matter=first == 0)
        if separator.end - separator.start not in separator.admitted
    ]
    changed = [1] if first else []
    changed.extend(first + separator.end + 1 for separator in edits)
    if lines[last + 1 :] != [""]:
        changed.append(last + 1)
    if not changed:
        return MarkdownLayout(text, ())
    for separator in sorted(edits, reverse=True):
        least = min(separator.admitted)
        blank = least if separator.end - separator.start < least else max(separator.admitted)
        body[separator.start : separator.end] = [""] * blank
    laid_out = "\n".join(body) + "\n"
    same = _structure(laid_out) == _structure(text)
    return MarkdownLayout(laid_out if same else None, tuple(sorted(changed)))


def _separators(body: list[str], *, front_matter: bool) -> list[_Separator]:
    """Return every separator between blocks whose layout the paradigm owns."""
    closing = _front_matter_end(body) if front_matter else None
    offset = 0 if closing is None else closing + 1
    tree = _tree(body, offset)
    units = sorted([*_definitions(body, offset, tree), *tree], key=lambda unit: unit.first)
    if closing is not None:
        units.insert(0, _Block(0, closing, "front-matter", []))
    separators = [
        _Separator(before.last + 1, after.first, _document_admitted(before, after))
        for before, after in pairwise(units)
    ]
    for block in tree:
        separators.extend(_list_separators(body, block))
    return separators


def _front_matter_end(lines: list[str]) -> int | None:
    """Return the index of the line closing leading front matter, if the document has one."""
    if lines[0] != _FRONT_MATTER:
        return None
    return next((index for index in range(1, len(lines)) if lines[index] == _FRONT_MATTER), None)


def _tree(body: list[str], offset: int) -> list[_Block]:
    """Parse the body after any front matter into top-level blocks and their children."""
    stack: list[list[_Block]] = [[]]
    for token in _PARSER.parse("\n".join(body[offset:])):
        if token.nesting == -1:
            stack.pop()
            continue
        children: list[_Block] = []
        if token.type != "inline" and token.map is not None:
            start, end = (offset + line for line in token.map)
            last = max(index for index in range(start, end) if body[index].strip())
            ignores = token.type == "html_block" and token.content.strip() == _IGNORE
            stack[-1].append(_Block(start, last, token.type, children, ignores))
        if token.nesting == 1:
            stack.append(children)
    return stack[0]


def _definitions(body: list[str], offset: int, tree: list[_Block]) -> list[_Block]:
    """Return the runs of reference definitions, the only blocks the parser emits no token for."""
    covered = {index for block in tree for index in range(block.first, block.last + 1)}
    runs: list[_Block] = []
    for index in range(offset, len(body)):
        if body[index].strip() and index not in covered:
            if runs and runs[-1].last == index - 1:
                runs[-1] = runs[-1]._replace(last=index)
            else:
                runs.append(_Block(index, index, "definition", []))
    return runs


def _document_admitted(before: _Block, after: _Block) -> frozenset[int]:
    """Admit the blank lines the formatter writes between two adjacent document blocks."""
    if before.kind == after.kind == "definition":
        return _JOINED
    return _pair_admitted(before, after, _SEPARATED)


def _pair_admitted(before: _Block, after: _Block, default: frozenset[int]) -> frozenset[int]:
    """Join the node after a formatter-ignore comment, and let adjacent HTML blocks touch."""
    if before.ignores_next:
        return _JOINED
    if before.kind == after.kind == "html_block":
        return _EITHER
    return default


def _list_separators(body: list[str], block: _Block) -> Iterator[_Separator]:
    """Return the separators within every list a block holds, outside quotes and tables."""
    if block.kind in _OPAQUE:
        return
    if block.kind in _LISTS:
        for item, following in pairwise(block.children):
            admitted = _SEPARATED if _spread(item) else _JOINED
            yield _Separator(item.last + 1, following.first, admitted)
    if block.kind == "list_item_open" and _spread(block):
        for child, following in pairwise(block.children):
            if any(body[index].strip() for index in range(child.last + 1, following.first)):
                continue
            joined = child.kind == "paragraph_open" and following.kind in _LISTS
            admitted = _EITHER if joined else _pair_admitted(child, following, _SEPARATED)
            yield _Separator(child.last + 1, following.first, admitted)
    for child in block.children:
        yield from _list_separators(body, child)


def _spread(item: _Block) -> bool:
    """Return whether a blank line separates any two blocks of a list item."""
    return any(child.last + 1 < following.first for child, following in pairwise(item.children))


def _structure(text: str) -> tuple[object, ...]:
    """Return a document's front matter, references and block structure, without its spacing."""
    lines = text.split("\n")
    closing = _front_matter_end(lines)
    offset = 0 if closing is None else closing + 1
    environment: dict[str, dict[str, dict[str, object]]] = {}
    tokens = _PARSER.parse("\n".join(lines[offset:]), environment)
    references = environment.get("references", {})
    return (
        tuple(lines[:offset]),
        tuple(
            (label, reference["href"], reference["title"])
            for label, reference in sorted(references.items())
        ),
        tuple(
            (token.type, token.tag, token.markup, token.info)
            + ((token.content,) if token.type in _LITERAL else ())
            for token in tokens
        ),
    )
