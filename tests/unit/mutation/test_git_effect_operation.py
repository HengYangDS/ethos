"""Name the ref when a candidate integration matches no declared branch role."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effects as git_effects
from tests.support.git_effect import ISSUER
from tests.support.git_effect import effect
from tests.support.git_effect import fixture
from tests.support.git_effect import plan
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path


def test_unclassified_candidate_integration_names_its_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A candidate integration refuses a ref that no branch role classifies, before any intent."""
    case = fixture(tmp_path)
    value = effect(case.old, case.new, ref="refs/heads/unrelated")
    carried = plan(
        case.repo,
        value,
        policy={
            "operation": "git.ref.compare-and-swap",
            "transition": "candidate.integrate",
            "effect_digest": value.digest(),
        },
    )
    monkeypatch.setattr(
        git_effects,
        "admit_git_effect_state",
        lambda *_args, **_kwargs: ({}, False, "repository:repo"),
    )

    unresolved = "ref_transition_operation_unresolved:refs/heads/unrelated"
    with pytest.raises(ValueError, match=unresolved):
        git_effects.execute_git_effect(case.repo, carried, issuer=ISSUER)

    assert git(case.repo, "for-each-ref", "refs/heads/unrelated") == ""
