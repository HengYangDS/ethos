"""OpenSpec conventions of the repository paradigm.

A repository that tracks OpenSpec artifacts selects the shared artifact schema, and
each artifact's rules in its OpenSpec configuration begin with the paradigm's common
rules; the repository's own rules follow them.
"""

from __future__ import annotations

import re
import textwrap
from typing import TYPE_CHECKING

import yaml

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Sequence
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm

CONFIGURATION = "openspec/config.yaml"
_ROOT = "openspec/"
_ALTERNATE = "openspec/config.yml"
_KEY = re.compile(r"(?P<indent> *)(?P<key>[A-Za-z_][\w-]*):(?P<value>(?:[ \t].*)?)")
_ITEM = re.compile(r"-(?:[ \t]|$)")
_MARKERS = ("---", "...", "%")

Repair = tuple[str, str]


def openspec_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Report a configuration that selects another schema or omits common artifact rules."""
    if not any(path.startswith(_ROOT) for path in tracked):
        return
    if _ALTERNATE in tracked:
        repair = (
            f"remove {_ALTERNATE}; {CONFIGURATION} is the OpenSpec configuration"
            if CONFIGURATION in tracked
            else f"rename {_ALTERNATE} to {CONFIGURATION}"
        )
        yield ParadigmGap("openspec-configuration", _ALTERNATE, repair)
        return
    text = tracked_text(root, CONFIGURATION, tracked)
    declared = _configuration(text or "")
    if declared is None or (text is None and CONFIGURATION in tracked):
        yield ParadigmGap(
            "openspec-configuration",
            CONFIGURATION,
            f"make {CONFIGURATION} a readable YAML mapping",
        )
        return
    conventions = paradigm.openspec
    if declared.get("schema") != conventions.artifact_schema:
        yield ParadigmGap(
            "openspec-schema",
            f"{CONFIGURATION}:schema",
            f"set schema to {conventions.artifact_schema}",
        )
    rules = declared.get("rules")
    for artifact, common in conventions.rules.model_dump(mode="json").items():
        declared_rules = rules.get(artifact) if isinstance(rules, dict) else None
        if not isinstance(declared_rules, list) or declared_rules[: len(common)] != common:
            yield ParadigmGap(
                "openspec-rules",
                f"{CONFIGURATION}:rules.{artifact}",
                f"begin rules.{artifact} with the paradigm's common {artifact} rules "
                "and keep the repository's own rules after them",
            )


def schema_repair(
    paradigm: RepositoryParadigm, _gap: ParadigmGap, text: str | None
) -> Repair | None:
    """Add the shared schema to a configuration that selects none.

    Replacing another selected schema needs judgment: the repository may own that
    schema and Changes written against its artifacts.
    """
    lines = _lines(text)
    if not _simple_keys(lines, 0, 0, len(lines)) or _key_indices(lines, "schema", 0, 0, len(lines)):
        return None
    schema = paradigm.openspec.artifact_schema
    first = next((index for index, line in enumerate(lines) if _KEY.fullmatch(line)), len(lines))
    lines.insert(first, f"schema: {schema}")
    return _verified(lines, text, {"schema": schema})


def common_rules_repair(
    paradigm: RepositoryParadigm, gap: ParadigmGap, text: str | None
) -> Repair | None:
    """Put one artifact's common rules first and keep the repository's own rules after them.

    The repository's own items keep their exact lines and the comments above them. A
    flow sequence becomes a block sequence; any shape the edit cannot isolate stays
    report-only.
    """
    artifact = gap.carrier.rpartition(".")[2]
    common = list(paradigm.openspec.rules.model_dump(mode="json")[artifact])
    declared = _configuration(text or "")
    rules = declared.get("rules") if declared is not None else None
    current = rules.get(artifact) if isinstance(rules, dict) else None
    if (
        declared is None
        or not isinstance(rules, dict | None)
        or not isinstance(current, list | None)
        or not all(isinstance(rule, str) for rule in current or ())
    ):
        return None
    width = next(
        (
            formatter.settings.get("printWidth")
            for formatter in paradigm.formatter
            if CONFIGURATION.endswith(formatter.suffixes)
        ),
        None,
    )
    own = [rule for rule in current or () if rule not in common]
    edited = (
        _with_rules(_lines(text), artifact, common, own, width) if isinstance(width, int) else None
    )
    if edited is None:
        return None
    return _verified(edited, text, {"rules": {**(rules or {}), artifact: [*common, *own]}})


def _with_rules(
    lines: list[str], artifact: str, common: list[str], own: list[str], width: int
) -> list[str] | None:
    """Rewrite one artifact's rules under the top-level rules key, adding either when absent."""
    found = _key_indices(lines, "rules", 0, 0, len(lines))
    if (
        not _simple_keys(lines, 0, 0, len(lines))
        or len(found) > 1
        or (found and _inline(lines[found[0]]))
    ):
        return None
    if not found:
        separator = [""] if lines and lines[-1].strip() else []
        return [*lines, *separator, "rules:", f"  {artifact}:", *_items(common, 4, width)]
    start = found[0]
    end = _extent(lines, start, 0)
    children = [index for index in range(start + 1, end) if _content(lines[index])]
    indent = _indent(lines[children[0]]) if children else 2
    named = _key_indices(lines, artifact, indent, start + 1, end)
    if not _simple_keys(lines, indent, start + 1, end) or len(named) > 1:
        return None
    if named:
        return _artifact_rules(lines, named[0], indent, (common, own), width)
    key = f"{' ' * indent}{artifact}:"
    return [*lines[:end], key, *_items(common, indent + 2, width), *lines[end:]]


def _artifact_rules(
    lines: list[str],
    position: int,
    indent: int,
    rules: tuple[list[str], list[str]],
    width: int,
) -> list[str] | None:
    """Rewrite the block or flow sequence of the artifact key on one line."""
    common, own = rules
    close = _extent(lines, position, indent, sequence=True)
    inline = _inline(lines[position])
    if inline:
        # A flow sequence on the key line is rewritten as a block; a trailing comment or
        # a sequence spanning lines cannot be carried over without guessing.
        if close != position + 1 or not inline.startswith("[") or "#" in inline:
            return None
        key = lines[position][: lines[position].index(":") + 1]
        return [*lines[:position], key, *_items([*common, *own], indent + 2, width), *lines[close:]]
    block = _kept(lines[position + 1 : close], common, indent + 2)
    if block is None:
        return None
    item_indent, leading, kept = block
    rendered = _items(common, item_indent, width)
    return [*lines[: position + 1], *leading, *rendered, *kept, *lines[close:]]


def _kept(
    block: list[str], common: list[str], default_indent: int
) -> tuple[int, list[str], list[str]] | None:
    """Split a block sequence into its leading lines and the repository's own items.

    Lines above the first item stay under the artifact key. Each later item owns the
    blank and comment lines directly above it, so an own item keeps its comment and a
    dropped copy of a common rule takes its comment along.
    """
    content = [index for index, line in enumerate(block) if _content(line)]
    if not content:
        return default_indent, block, []
    item_indent = _indent(block[content[0]])
    starts = [index for index in content if _indent(block[index]) == item_indent]
    if not all(_ITEM.match(block[index][item_indent:]) for index in starts):
        return None
    leads = [starts[0], *(_lead(block, index) for index in starts[1:])]
    kept: list[str] = []
    for lead, following in zip(leads, [*leads[1:], len(block)], strict=True):
        span = block[lead:following]
        value = _parsed("\n".join(line[min(item_indent, _indent(line)) :] for line in span))
        if not (isinstance(value, list) and len(value) == 1 and isinstance(value[0], str)):
            return None
        if value[0] not in common:
            kept.extend(span)
    return item_indent, block[: leads[0]], kept


def _items(rules: Sequence[str], indent: int, width: int) -> list[str]:
    """Render rules as block sequence items wrapped within the paradigm's line width."""
    lines: list[str] = []
    for rule in rules:
        wrapped = textwrap.wrap(
            rule, max(width - indent - 2, 20), break_long_words=False, break_on_hyphens=False
        )
        item = [f"- {wrapped[0]}", *(f"  {line}" for line in wrapped[1:])] if wrapped else []
        if _parsed("\n".join(item)) != [rule]:
            item = yaml.safe_dump([rule], width=width - indent, allow_unicode=True).split("\n")[:-1]
        lines.extend(f"{' ' * indent}{line}" for line in item)
    return lines


def _verified(lines: list[str], text: str | None, changes: dict[str, object]) -> Repair | None:
    """Keep a rewrite only when it parses to the original configuration with the changes."""
    repaired = "\n".join(lines) + "\n"
    expected = {**(_configuration(text or "") or {}), **changes}
    return (repaired, "") if _configuration(repaired) == expected else None


def _configuration(text: str) -> dict[str, object] | None:
    """Return the parsed configuration mapping, empty for an empty document, or None."""
    declared = _parsed(text)
    if declared is None and not text.strip():
        return {}
    return declared if isinstance(declared, dict) else None


def _parsed(text: str) -> object:
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _lines(text: str | None) -> list[str]:
    return text.rstrip("\n").split("\n") if text and text.strip() else []


def _simple_keys(lines: list[str], indent: int, start: int, end: int) -> bool:
    """Require every key at one indentation of a parsed mapping to be a plain `key:` line.

    Item lines at that indentation belong to the compact sequence of the key above them.
    """
    return all(
        _KEY.fullmatch(line) or _ITEM.match(line[indent:]) or line.startswith(_MARKERS)
        for line in lines[start:end]
        if _content(line) and _indent(line) == indent
    )


def _key_indices(lines: list[str], name: str, indent: int, start: int, end: int) -> list[int]:
    return [
        index
        for index in range(start, end)
        if (match := _KEY.fullmatch(lines[index]))
        and len(match["indent"]) == indent
        and match["key"] == name
    ]


def _inline(line: str) -> str:
    """Return a key line's inline value, without a trailing comment-only remainder."""
    match = _KEY.fullmatch(line)
    value = match["value"].strip() if match else ""
    return "" if value.startswith("#") else value


def _extent(lines: list[str], start: int, indent: int, *, sequence: bool = False) -> int:
    """Return the index past the last content line of the block a key line opens."""
    end = start + 1
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if not _content(line):
            continue
        depth = _indent(line)
        if not (depth > indent or (sequence and depth == indent and _ITEM.match(line[depth:]))):
            break
        end = index + 1
    return end


def _lead(block: list[str], start: int) -> int:
    while start > 0 and not _content(block[start - 1]):
        start -= 1
    return start


def _content(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
