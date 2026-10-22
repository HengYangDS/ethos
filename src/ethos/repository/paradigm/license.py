"""A tracked license grant: one recognized standard text, linked and consistently declared.

The license a repository chooses is its own. Its grant is recognized when the text matches
one packaged SPDX template under the SPDX matching guidelines: spacing, case, quotation
and dash forms and the HTTP scheme do not count, replaceable text matches its template
pattern and optional text may be absent. A copyright notice the template requires must
name its holder rather than keep the template placeholder, and only the template's own
title may precede it. A license outside the SPDX list is the repository's own text, which
its package metadata names by a `LicenseRef-` identifier.
"""

from __future__ import annotations

import json
import posixpath
import re
import tomllib
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from packaging.licenses import InvalidLicenseExpression
from packaging.licenses import canonicalize_license_expression

from ethos.contracts.paradigm.declaration import license_template
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.gap import tracked_text
from ethos.repository.registry.docs.links import markdown_links

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import LicenseConventions
    from ethos.contracts.paradigm.declaration import RepositoryParadigm

_MANIFESTS = ("package.json", "package-lock.json", "pyproject.toml")
_MARKUP = re.compile(r'<<(beginOptional|endOptional|var;(?:[^"]|"[^"]*")*?)>>')
_FIELD = re.compile(r'(\w+)="([^"]*)"')
_EQUIVALENT = str.maketrans("\u2018\u2019\u201c\u201d\u2013\u2014", "''\"\"--")


def license_gaps(
    paradigm: RepositoryParadigm, root: Path, tracked: frozenset[str]
) -> Iterator[ParadigmGap]:
    """Judge the grant, its public entry and the license each root manifest declares."""
    conventions = paradigm.license
    carrier = conventions.carrier
    declared = _declared_licenses(root, tracked)
    if carrier not in tracked:
        if any(isinstance(value, str) and value != "UNLICENSED" for value in declared.values()):
            repair = f"add {carrier} with the standard text of the license package metadata names"
            yield ParadigmGap("license-grant", carrier, repair)
        return
    identifier = _recognized(tracked_text(root, carrier, tracked) or "", conventions)
    identifier = identifier or _custom_license(declared)
    if identifier is None:
        recognized = ", ".join(sorted(conventions.templates))
        repair = (
            f"keep the standard text of one recognized license ({recognized}) in {carrier},"
            " naming its copyright holder, or declare its own license by a LicenseRef-"
            " identifier in the package metadata"
        )
        yield ParadigmGap("license-grant", carrier, repair)
    if not _links_grant(root, conventions, tracked):
        repair = f"link {carrier} from {conventions.entry}"
        yield ParadigmGap("license-entry", conventions.entry, repair)
    for manifest, value in declared.items():
        if identifier is not None and not _consistent(value, identifier, carrier):
            repair = f"declare license {identifier} in {manifest}, as {carrier} grants it"
            yield ParadigmGap("license-metadata", manifest, repair)


def _declared_licenses(root: Path, tracked: frozenset[str]) -> dict[str, object]:
    """Return the license each tracked root package manifest declares, by manifest."""
    owners = {
        manifest: _license_owner(manifest, tracked_text(root, manifest, tracked))
        for manifest in _MANIFESTS
    }
    return {
        manifest: owner["license"]
        for manifest, owner in owners.items()
        if isinstance(owner, dict) and "license" in owner
    }


def _license_owner(manifest: str, source: str | None) -> object:
    """Return the object or table that carries one root manifest's own license."""
    if source is None:
        return None
    try:
        if manifest == "pyproject.toml":
            return tomllib.loads(source).get("project")
        payload = json.loads(source)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError):
        return None
    if manifest == "package-lock.json" and isinstance(payload, dict):
        packages = payload.get("packages")
        return packages.get("") if isinstance(packages, dict) else None
    return payload


def _custom_license(declared: dict[str, object]) -> str | None:
    """Return the identifier a manifest gives a license outside the SPDX list, if any."""
    custom = (
        value
        for value in declared.values()
        if isinstance(value, str) and value.startswith("LicenseRef-")
    )
    return next(custom, None)


def _consistent(value: object, identifier: str, carrier: str) -> bool:
    """Accept the same SPDX expression, or npm's reference to the grant file itself."""
    if not isinstance(value, str):
        return False
    if value == f"SEE LICENSE IN {carrier}":
        return True
    try:
        return canonicalize_license_expression(value) == identifier
    except InvalidLicenseExpression:
        return False


def _links_grant(root: Path, conventions: LicenseConventions, tracked: frozenset[str]) -> bool:
    """Return whether the public entry links the grant by a relative destination."""
    entry = conventions.entry
    try:
        links = markdown_links(root / entry) if entry in tracked else []
    except (OSError, UnicodeError):
        links = []
    for _line, target in links:
        parts = urlsplit(target)
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(entry), parts.path))
        if not parts.scheme and not parts.netloc and resolved == conventions.carrier:
            return True
    return False


def _recognized(text: str, conventions: LicenseConventions) -> str | None:
    """Return the identifier of the template the grant matches with its holder named."""
    normalized = _normalize(text)
    for identifier in sorted(conventions.templates):
        pattern, notices = _template(identifier)
        matched = pattern.fullmatch(normalized)
        if matched and all(_named(matched.group(group), hint) for group, hint in notices):
            return identifier
    return None


@lru_cache
def _template(identifier: str) -> tuple[re.Pattern[str], tuple[tuple[str, str], ...]]:
    """Compile one SPDX template and name the copyright notices its required text holds."""
    template = license_template(identifier)
    parts: list[str] = []
    notices: list[tuple[str, str]] = []
    depth = cursor = 0
    for markup in _MARKUP.finditer(template):
        parts.append(_literal(template[cursor : markup.start()]))
        cursor, token = markup.end(), markup.group(1)
        if token == "beginOptional":
            depth += 1
            parts.append("(?:")
        elif token == "endOptional":
            depth -= 1
            parts.append(")?")
        else:
            fields = dict(_FIELD.findall(token))
            group = f"v{len(parts)}"
            if fields["name"] == "copyright" and depth == 0:
                notices.append((group, _normalize(fields["original"])))
            parts.append(f"(?P<{group}>{fields['match']})")
    parts.append(_literal(template[cursor:]))
    return re.compile("".join(parts), re.IGNORECASE | re.DOTALL), tuple(notices)


def _literal(text: str) -> str:
    words = _normalize(text).split()
    return r"\s*" + r"\s+".join(map(re.escape, words)) + r"\s*" if words else r"\s*"


def _normalize(text: str) -> str:
    return " ".join(text.translate(_EQUIVALENT).replace("https://", "http://").split())


def _named(notice: str | None, placeholder: str) -> bool:
    """Return whether a required notice states its copyright first and names its holder.

    The notice pattern accepts any text, so a title other than the template's own would
    otherwise pass as part of the notice.
    """
    normalized = _normalize(notice or "")
    matched = re.fullmatch(
        r"copyright\b\s*(?:\(c\)|©)?\s*(?:\d{4}(?:\s*[-,]\s*\d{4})*\s*)?(?P<holder>.*)",
        normalized,
        re.IGNORECASE,
    )
    if matched is None or placeholder.lower() in normalized.lower():
        return False
    holder = matched.group("holder")
    return any(character.isalpha() for character in holder) and not re.search(
        r"<[^>]*>|\[[^]]*\]", holder
    )
