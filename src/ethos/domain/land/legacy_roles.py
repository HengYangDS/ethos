"""Closeout's rename of legacy role refs as one public land result."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.mutation.branch_roles import rename_legacy_roles
from ethos.adapters.mutation.branch_roles import resume_renamed_bindings
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.verdict import Verdict


def legacy_role_rename_result(
    repo: Path, *, apply: bool, authorize: bool, expect_head: str | None
) -> EthosResult | None:
    """Finish an interrupted binding, then rename legacy role refs before any acceptance."""
    resume_renamed_bindings(repo)
    renamed = rename_legacy_roles(
        repo,
        current_head=git.current_head(repo),
        apply=apply,
        authorized=authorize,
        expect_head=expect_head,
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
