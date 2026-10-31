"""Per-file size ceilings: the contract's defaults, a repository's own values and the measure.

A repository binding may declare a ceiling in `.ethos/rules.toml` `[paradigm.size]`: a lower
value applies, and a higher one applies within the contract's bound when
`[paradigm.size.reasons]` states why. Any other declaration is a gap and leaves the default in
force, so a malformed value never widens a ceiling. The code ceiling bounds every authored file
of a registered language.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.measure import effective_code_lines_for_source
from ethos.measure import lexed_effective_lines
from ethos.repository.paradigm.gap import ParadigmGap

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import RepositoryParadigm


class SizeResolution(NamedTuple):
    """The effective ceilings, the declaration's gaps and each reasoned higher value."""

    ceilings: dict[str, int]
    gaps: tuple[ParadigmGap, ...]
    deviations: tuple[dict[str, object], ...]


def size_resolution(rules: str | None, paradigm: RepositoryParadigm) -> SizeResolution:
    """Resolve each ceiling from the contract default and the binding's `rules.toml` text."""
    ceilings = paradigm.size.model_dump(exclude={"bound", "retired"})
    carrier = f"{paradigm.binding.root}/rules.toml"
    try:
        table = tomllib.loads(rules or "")
    except tomllib.TOMLDecodeError:
        table = {}
    gaps: list[ParadigmGap] = []
    if "code_size" in _table(table, "quality"):
        repair = "replace [quality.code_size] with a repository value in [paradigm.size]"
        gaps.append(ParadigmGap("binding-restatement", f"{carrier}:quality.code_size", repair))
    declared = _table(_table(table, "paradigm"), "size")
    reasons = _table(declared, "reasons")
    deviations: list[dict[str, object]] = []
    for key, value in declared.items():
        if key == "reasons":
            continue
        default = ceilings.get(key)
        reason = reasons.get(key)
        place = f"{carrier}:paradigm.size.{key}"
        if default is None:
            renamed = paradigm.size.retired.get(key)
            repair = f"rename {key} to {renamed}" if renamed else f"remove {key}"
            gaps.append(ParadigmGap("size-declaration", place, repair))
        elif type(value) is not int or value <= 0:
            repair = f"declare {key} as a positive integer"
            gaps.append(ParadigmGap("size-declaration", place, repair))
        elif value == default:
            repair = f"remove {key}; {default} is the paradigm's default"
            gaps.append(ParadigmGap("binding-restatement", place, repair))
        elif value > paradigm.size.bound or (value > default and not _stated(reason)):
            repair = f"declare {key} at most {paradigm.size.bound} with its reason, or remove it"
            gaps.append(ParadigmGap("size-declaration", place, repair))
        else:
            ceilings[key] = value
            if value > default:
                deviations.append(
                    {"ceiling": key, "value": value, "default": default, "reason": reason}
                )
    return SizeResolution(ceilings, tuple(gaps), tuple(deviations))


def repository_ceilings(root: Path) -> dict[str, int]:
    """Return the effective ceilings that the repository's binding selects."""
    paradigm = load_repository_paradigm()
    try:
        rules = (root / paradigm.binding.root / "rules.toml").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        rules = None
    return size_resolution(rules, paradigm).ceilings


def code_size_gaps(
    paradigm: RepositoryParadigm,
    root: Path,
    authored_paths: Iterable[str],
    ceiling: int,
) -> tuple[ParadigmGap, ...]:
    """Measure every authored file of a registered language against the code ceiling."""
    gaps: list[ParadigmGap] = []
    for path in sorted(set(authored_paths)):
        language = paradigm.language_of(path)
        carrier = root / path
        if language is None or not carrier.is_file():
            continue
        try:
            source = carrier.read_text(encoding="utf-8")
            if language.measure == "lexer":
                effective = lexed_effective_lines(source, language.lexer)
            else:
                effective = effective_code_lines_for_source(source)
        except (OSError, UnicodeError, SyntaxError, ValueError):
            repair = f"make {path} readable UTF-8 {language.id} source so it can be measured"
            gaps.append(ParadigmGap("code-size", path, repair))
            continue
        if effective > ceiling:
            repair = (
                f"split {path} by semantic ownership into a subdirectory of modules, "
                f"each at most {ceiling} effective lines"
            )
            gaps.append(ParadigmGap("code-size", path, repair))
    return tuple(gaps)


def _table(value: object, key: str) -> dict[str, object]:
    """Return one TOML table, or an empty one when it is absent or not a table."""
    table = value.get(key) if isinstance(value, dict) else None
    return table if isinstance(table, dict) else {}


def _stated(reason: object) -> bool:
    """Return whether a declared reason is a non-empty string."""
    return isinstance(reason, str) and bool(reason.strip())
