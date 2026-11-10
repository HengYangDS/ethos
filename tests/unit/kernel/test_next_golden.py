"""`next` classifies each group argv at least as strictly as the argv tables it replaces.

`tests/fixtures/next-golden.json` was written once, at `ff8de8f41`, by a generator kept in owned
scratch and never committed (`build/runtime/work/catalog-root/catalog-groups/s1-spike/`
`generate_next_golden.py`, which extends the committee's `golden/generate_next_golden.py`). It ran
the former classifiers over each group leaf with every subset of its mode-bearing flags and over the
product-rendered group argv, and recorded the exit the former surface chose. Those classifiers
retire with this Change, so the data cannot be regenerated and a change to it is reviewed. An argv
whose leaf is not yet a catalog entry keeps the former answer exactly. A row marked `refused` is an
argv that its catalog entry refuses, as it sets a field its operation does not take or modes that
no operation combines; each slice marks the rows it refuses.
"""

import json
import shlex
from pathlib import Path
from typing import get_args

import pytest

from ethos.contracts.admission import StepAuthorization
from ethos.contracts.next_step import derive_next_step
from ethos.contracts.operations.catalog import select_argv

_ROWS = json.loads((Path(__file__).parents[2] / "fixtures/next-golden.json").read_text())["rows"]
_RANK = get_args(StepAuthorization)


@pytest.mark.parametrize("row", _ROWS, ids=lambda row: shlex.join(row["argv"][1:]))
def test_each_group_argv_is_classified_at_least_as_strictly_as_before(row) -> None:
    """Effects a superset, authority and deletion not lower and the same exit, or refused."""
    text = shlex.join(row["argv"])
    step = derive_next_step(text, continuation="continue", why="golden")
    selected = select_argv(row["argv"])
    if row.get("refused"):
        refused = ("", ("opaque",), "human", True)
        assert (step.form, step.effects, step.authorization, step.destructive) == refused
    elif selected is None:
        old = (row["effects"], row["authorization"], row["destructive"])
        assert (list(step.effects), step.authorization, step.destructive) == old
    else:
        assert selected[1] is not None
        assert selected[1].exit == row["exit"]
        assert set(row["effects"]) <= set(step.effects)
        assert _RANK.index(step.authorization) >= _RANK.index(row["authorization"])
        assert step.destructive >= row["destructive"]
