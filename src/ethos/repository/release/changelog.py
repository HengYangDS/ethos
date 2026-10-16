"""Validate the common release-note contract over parsed Markdown and SemVer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt
from semver import Version

from ethos.contracts.paradigm.declaration import load_repository_paradigm

if TYPE_CHECKING:
    from markdown_it.token import Token

_CATEGORIES = frozenset({"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"})


def semver_from_text(text: str) -> str:
    """Read an exact version carrier without imposing ETHOS's wheel profile."""
    value = text.strip()
    if text != value + "\n":
        message = "release_version_source_not_canonical"
        raise ValueError(message)
    return str(Version.parse(value))


@dataclass(frozen=True)
class _Section:
    title: str
    body: tuple[Token, ...]


@dataclass(frozen=True)
class _Entry:
    label: str
    version: Version | None
    released_on: date | None
    body: tuple[Token, ...]


def _sections(tokens: tuple[Token, ...], tag: str) -> tuple[_Section, ...]:
    """Select real document-level headings, never fenced or nested examples."""
    boundaries = [
        index
        for index, token in enumerate(tokens)
        if token.type == "heading_open" and token.tag <= tag and token.level == 0
    ]
    stops = [*boundaries[1:], len(tokens)] if boundaries else []
    return tuple(
        _Section(_heading_label(tokens[start + 1]), tokens[start + 3 : stop])
        for start, stop in zip(boundaries, stops, strict=True)
        if tokens[start].tag == tag
    )


def _heading_label(inline: Token) -> str:
    """Retain version brackets when Markdown resolves their history links."""
    return "".join(
        {"link_open": "[", "link_close": "]"}.get(child.type, child.content)
        for child in inline.children or ()
    )


def _entry(section: _Section, heading: re.Pattern[str]) -> _Entry:
    matched = heading.fullmatch("## " + section.title)
    if matched is None:
        message = f"release_changelog_heading_invalid:{section.title}"
        raise ValueError(message)
    label, day = matched.group("version", "date")
    if label == "Unreleased":
        if day is not None:
            message = "release_changelog_unreleased_date"
            raise ValueError(message)
        return _Entry(label, None, None, section.body)
    try:
        version = Version.parse(label)
    except ValueError as error:
        message = f"release_changelog_version_invalid:{label}"
        raise ValueError(message) from error
    try:
        released_on = date.fromisoformat(day or "")
    except ValueError as error:
        message = f"release_changelog_date_invalid:{label}"
        raise ValueError(message) from error
    return _Entry(label, version, released_on, section.body)


def _meaningful(tokens: tuple[Token, ...]) -> bool:
    """Require note text, not an empty list, comment or another heading."""
    return any(
        token.type == "inline"
        and (index == 0 or tokens[index - 1].type != "heading_open")
        and any(
            child.type in {"text", "code_inline"} and child.content.strip()
            for child in token.children or ()
        )
        for index, token in enumerate(tokens)
    )


def _category_errors(entry: _Entry) -> tuple[str, ...]:
    sections = _sections(entry.body, "h3")
    if not sections and entry.version is not None:
        return (f"release_changelog_categories_missing:{entry.label}",)
    seen: set[str] = set()
    errors = []
    prefix_end = next(
        (
            index
            for index, token in enumerate(entry.body)
            if token.type == "heading_open" and token.tag == "h3" and token.level == 0
        ),
        len(entry.body),
    )
    if any(
        token.type == "inline" and _meaningful((token,)) and not _history_index(token)
        for token in entry.body[:prefix_end]
    ):
        errors.append(f"release_changelog_content_uncategorized:{entry.label}")
    for section in sections:
        for failed, reason in (
            (section.title not in _CATEGORIES, "category_invalid"),
            (section.title in seen, "category_duplicate"),
            (not _meaningful(section.body), "category_empty"),
        ):
            if failed:
                errors.append(f"release_changelog_{reason}:{entry.label}:{section.title}")
        seen.add(section.title)
    return tuple(errors)


def _history_index(inline: Token) -> bool:
    """Permit a history-link index without treating its URLs as verified facts."""
    links, linked = 0, False
    outside = []
    for child in inline.children or ():
        if child.type == "link_open":
            links += 1
            linked = True
        elif child.type == "link_close":
            linked = False
        elif not linked:
            outside.append(child.content)
    return bool(links) and not "".join(outside).strip().removeprefix("History:").strip(" ·|,;")


def _history_errors(entries: tuple[_Entry, ...]) -> tuple[str, ...]:
    errors = []
    labels = [entry.label for entry in entries]
    if labels.count("Unreleased") != 1:
        errors.append("release_changelog_unreleased_count")
    elif labels[0] != "Unreleased":
        errors.append("release_changelog_unreleased_order")
    seen: set[str] = set()
    previous: _Entry | None = None
    for entry in entries:
        if entry.label in seen:
            errors.append(f"release_changelog_version_duplicate:{entry.label}")
        seen.add(entry.label)
        errors.extend(_category_errors(entry))
        if entry.version is None:
            continue
        if previous is not None:
            assert previous.version is not None
            assert entry.released_on is not None
            assert previous.released_on is not None
            if entry.version.compare(previous.version) > 0:
                errors.append(f"release_changelog_version_order:{entry.label}")
            if entry.released_on > previous.released_on:
                errors.append(f"release_changelog_date_order:{entry.label}")
        previous = entry
    return tuple(errors)


def changelog_errors(text: str | None, *, target: str = "") -> tuple[str, ...]:
    """Validate source history and, only at release preparation, its exact target."""
    if text is None:
        return ("release_changelog_source_missing",)
    sections = _sections(tuple(MarkdownIt("commonmark").parse(text)), "h2")
    heading = re.compile(load_repository_paradigm().release.changelog_heading)
    entries = []
    errors = []
    for section in sections:
        try:
            entries.append(_entry(section, heading))
        except ValueError as error:
            errors.append(str(error))
    errors.extend(_history_errors(tuple(entries)))
    if target and not any(entry.label == target for entry in entries):
        errors.append(f"release_changelog_target_missing:{target}")
    return tuple(dict.fromkeys(errors))
