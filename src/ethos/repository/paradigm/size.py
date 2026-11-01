"""The per-file code ceiling's measure over every authored file of a registered language.

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
