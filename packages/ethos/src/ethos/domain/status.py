"""Status-stage domain reducers — pure functions over primitive facts.

No IO: these take already-resolved primitives (heads, flags, arbitrary values)
and derive gap tuples / normalized shapes. Fed by the surface/adapters layer.
"""

from __future__ import annotations


def string_list(value: object) -> list[str]:
    """Coerce an arbitrary value to list[str] (empty if not a list)."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def adoption_mutation_gaps(
    *,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    current_head: str,
) -> tuple[str, ...]:
    """Derive adoption-mutation precondition gaps (empty when not applying)."""
    if not apply:
        return ()
    gaps: list[str] = []
    if not authorize:
        gaps.append("authorization_required")
    if current_head == "untracked":
        gaps.append("git_repository_missing")
    if not expect_head:
        gaps.append("expect_head_required")
    elif expect_head != current_head:
        gaps.append("expected_head_mismatch")
    return tuple(gaps)
