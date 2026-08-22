from __future__ import annotations

import pytest

from ethos.contracts.change_lineage.predecessor_set import canonical_predecessor_set
from ethos.contracts.change_lineage.predecessor_set import predecessor_set_matches


def test_canonical_predecessor_set_preserves_the_exact_partial_order() -> None:
    current = "b" * 64
    additional = ("c" * 64, "a" * 64)

    assert canonical_predecessor_set(current=current, additional=additional) == (
        "a" * 64,
        current,
        "c" * 64,
    )


@pytest.mark.parametrize(
    ("additional", "gap"),
    [
        (("a" * 64, "a" * 64), "change_lineage_predecessor_duplicate"),
        (("b" * 64,), "change_lineage_current_predecessor_redeclared"),
    ],
)
def test_canonical_predecessor_set_rejects_ambiguous_repetition(
    additional: tuple[str, ...],
    gap: str,
) -> None:
    with pytest.raises(ValueError, match=gap):
        canonical_predecessor_set(current="b" * 64, additional=additional)


def test_canonical_predecessor_set_identifies_the_malformed_digest() -> None:
    with pytest.raises(ValueError, match="change_lineage_predecessor_invalid:not-a-digest"):
        canonical_predecessor_set(current="a" * 64, additional=("not-a-digest",))


def test_predecessor_set_matching_is_exact_not_subset_based() -> None:
    current = "a" * 64
    requested = ("b" * 64,)
    exact = canonical_predecessor_set(current=current, additional=requested)

    assert predecessor_set_matches(
        actual=exact,
        current=current,
        additional=requested,
    )
    assert not predecessor_set_matches(
        actual=(*exact, "c" * 64),
        current=current,
        additional=requested,
    )
    assert not predecessor_set_matches(
        actual=requested,
        current=current,
        additional=requested,
    )
    assert not predecessor_set_matches(
        actual=exact,
        current=current,
        additional=(requested[0], requested[0]),
    )
    assert not predecessor_set_matches(
        actual=("not-a-digest",),
        current="not-a-digest",
        additional=(),
    )
