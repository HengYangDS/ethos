"""Observe exact Git ref effects and compile their transient plans."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import committed_file_bytes
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_head
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from ethos.contracts.plan import GitEffect
    from ethos.contracts.plan import TransitionPlan
    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject

_MISMATCH = "git_effect_repository_identity_mismatch"
_ZERO_OIDS = {"0" * 40, "0" * 64, ""}


def observe_git_effect(
    root: Path,
    effect: GitEffect,
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Capture the exact Git facts before or after one effect."""
    head = current_tracked_head(root)
    return {
        "observed_at": datetime.now(UTC).isoformat(),
        "head": head,
        "tree": current_tree(root, head, environment=environment),
        "refs": {
            name: ref_head(root, name, update.expected, environment=environment)
            for name, update in effect.updates.items()
        },
        "assertions": {
            name: ref_head(root, name, environment=environment) for name in effect.assertions
        },
    }


def resolve_git_effect_repository(
    root: Path,
    effect: GitEffect,
    before: dict[str, object],
    *,
    environment: Mapping[str, str] | None = None,
    allow_missing_prestate: bool = False,
) -> str:
    """Resolve one repository identity across every revision touched by an effect."""
    env = dict(environment or {})
    expected = {update.expected for update in effect.updates.values()}
    revisions = {
        str(before["head"]),
        *(update.desired for update in effect.updates.values()),
        *effect.assertions.values(),
    } - _ZERO_OIDS
    try:
        identities = set()
        for revision in revisions:
            raw = committed_file_bytes(root, revision, ".ethos/commitment.toml", environment=env)
            if not raw and allow_missing_prestate and revision in expected:
                continue
            identities.add(load_repository_commitment(root, tree_ref=revision, environment=env).id)
        for revision in expected - _ZERO_OIDS:
            if committed_file_bytes(root, revision, ".ethos/commitment.toml", environment=env):
                identities.add(
                    load_repository_commitment(root, tree_ref=revision, environment=env).id
                )
    except ValueError as error:
        raise ValueError(_MISMATCH) from error
    if len(identities) != 1:
        raise ValueError(_MISMATCH)
    return identities.pop()


def compile_observed_git_effect(
    root: Path,
    commitment: Commitment,
    effect: GitEffect,
    *,
    head: str,
    policy: JsonObject,
    prior_attestations: JsonObject | None = None,
    values: Mapping[str, object] | None = None,
) -> TransitionPlan:
    """Compile one Git effect directly from fresh repository observations."""
    extra = dict(values or {})
    return compile_git_effect_plan(
        commitment,
        Facts(
            repository=commitment.id,
            head=head,
            tree=current_tree(root, head),
            observed_at=datetime.now(UTC),
            values={
                **extra,
                "refs": {ref: update.expected for ref, update in effect.updates.items()},
                "assertions": effect.assertions,
            },
            source_refs=(
                "git:HEAD",
                "git:HEAD^{tree}",
                *(f"git:{ref}" for ref in (*effect.updates, *effect.assertions)),
                *(("lease:current-generation",) if "lease_generation" in extra else ()),
            ),
        ),
        prior_attestations=prior_attestations or {},
        policy=policy,
        effect=effect,
    )
