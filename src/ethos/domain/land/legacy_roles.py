"""Closeout's rename of legacy role refs as one public land result."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.accepted.legacy_roles import rename_legacy_roles
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


def legacy_role_rename_result(
    repo: Path,
    *,
    apply: bool,
    authorize: bool,
    expect_head: str | None,
    expect_state: str | None = None,
) -> EthosResult | None:
    """Finish an interrupted binding, then rename legacy role refs before any acceptance."""
    try:
        renamed = rename_legacy_roles(
            repo,
            current_head=git.current_head(repo),
            apply=apply,
            authorized=authorize,
            expect_head=expect_head,
            expect_state=expect_state,
        )
    except ValueError as error:
        return EthosResult(
            command="land",
            verdict="block",
            state="blocked",
            required_gaps=(str(error),),
            next_action="ethos status --json",
        )
    if renamed is None:
        return None
    return EthosResult(
        command="land",
        verdict=cast("Verdict", renamed["verdict"]),
        state=str(renamed["state"]),
        required_gaps=tuple(string_sequence(renamed["required_gaps"])),
        next_action=str(renamed["next_action"]),
        data={"branch_role_rename": renamed},
    )
