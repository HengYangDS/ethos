"""The per-file code ceiling's measure of a file of a registered language.

The paradigm report applies it to every authored file and `pre-commit` to every staged one.

The ceiling itself is the `size` group's declared parameter, which a repository binding may set
by the rule in `ethos.repository.paradigm.parameters`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.measure import effective_code_lines_for_source
from ethos.measure import lexed_effective_lines
from ethos.repository.paradigm.gap import ParadigmGap

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from ethos.contracts.paradigm.declaration import Language
    from ethos.contracts.paradigm.declaration import RepositoryParadigm


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
            effective = effective_lines(language, carrier.read_text(encoding="utf-8"))
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


def effective_lines(language: Language, source: str) -> int:
    """Return one source text's effective lines under its language's measure.

    Source that the measure cannot read raises the measure's `SyntaxError` or `ValueError`.
    """
    if language.measure == "lexer":
        return lexed_effective_lines(source, language.lexer)
    return effective_code_lines_for_source(source)
