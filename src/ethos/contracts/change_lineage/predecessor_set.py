"""Pure predecessor-set invariants for governed Change lineage."""

from __future__ import annotations


def canonical_predecessor_set(
    *,
    current: str,
    additional: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the exact canonical predecessor set for one successor Change."""
    invalid = next(
        (
            digest
            for digest in (current, *additional)
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest)
        ),
        "",
    )
    if invalid:
        message = f"change_lineage_predecessor_invalid:{invalid}"
        raise ValueError(message)
    if len(additional) != len(set(additional)):
        message = "change_lineage_predecessor_duplicate"
        raise ValueError(message)
    if current in additional:
        message = "change_lineage_current_predecessor_redeclared"
        raise ValueError(message)
    return tuple(sorted((current, *additional)))


def predecessor_set_matches(
    *,
    actual: tuple[str, ...],
    current: str,
    additional: tuple[str, ...],
) -> bool:
    """Return whether one successor records exactly the requested lineage."""
    try:
        expected = canonical_predecessor_set(current=current, additional=additional)
    except ValueError:
        return False
    return actual == expected
