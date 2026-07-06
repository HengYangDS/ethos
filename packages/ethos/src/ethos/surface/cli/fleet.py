"""Fleet command group — external adopter inspection.

A surface command module: binds args, calls the domain/repository report, emits.
Registers onto the shared fleet_app from _base (import side-effect); cli.py imports
this module so the decorator runs. Imports only what this group needs.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs the runtime type for --target
from typing import cast

from ethos.adapters.repo import git as _gitio
from ethos.domain import land as _land
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.adoption.retirement import retirement_readiness_report
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity import shadow_parity_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import fleet_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


@fleet_app.command(name="inspect")
def fleet_inspect(
    *,
    target: Path,
    json_output: JsonFlag = False,
) -> None:
    """Inspect an external repository as an ETHOS adopter."""
    report = inspect_adopter(target)
    required_gaps = cast("list[str]", report["required_gaps"])
    result = EthosResult(
        command="fleet inspect",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "gapped",
        required_gaps=tuple(required_gaps),
        data=report,
    )
    emit(result, json_output, enforce=False)


@fleet_app.command(name="retirement-readiness")
def fleet_retirement_readiness(
    *,
    target: Path,
    execute_shadow: bool = False,
    timeout_seconds: int = 30,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check whether an adopter can retire its embedded ETHOS backend."""
    product_root = resolve_root(root)
    from ethos.repository.profile import load_repository_profile

    profile = load_repository_profile(target)
    adopter = profile.identity.get("profile_id") or target.resolve().name
    if execute_shadow:
        from ethos.adapters.shadow import run_shadow_parity

        shadow = run_shadow_parity(
            target=target,
            timeout_seconds=timeout_seconds,
            product_root=product_root,
        )
    else:
        shadow = shadow_parity_report(
            target=target,
            root=product_root,
            adopter=adopter,
            current_target_head=_gitio.current_tracked_head(target),
            current_product_head=_gitio.current_tracked_head(product_root),
            acceptable_product_heads=_land.acceptable_parity_product_heads(product_root, adopter),
            acceptable_target_heads=_land.acceptable_parity_target_heads(
                product_root, target, adopter
            ),
        )
    parity = parity_gaps_report(
        adopter=adopter,
        root=product_root,
        target=target,
        current_target_head=_gitio.current_tracked_head(target),
        current_product_head=_gitio.current_tracked_head(product_root),
        acceptable_product_heads=_land.acceptable_parity_product_heads(product_root, adopter),
        acceptable_target_heads=_land.acceptable_parity_target_heads(product_root, target, adopter),
    )
    report = retirement_readiness_report(
        target=target,
        product_root=product_root,
        parity_gaps=parity,
        shadow=shadow,
    )
    required_gaps = cast("list[str]", report["required_gaps"])
    next_actions = cast("list[str]", report["next_actions"])
    result = EthosResult(
        command="fleet retirement-readiness",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "adopter": report["adopter"],
            "gap_count": len(required_gaps),
        },
        required_gaps=tuple(required_gaps),
        next_actions=tuple(next_actions),
        data=report,
    )
    emit(result, json_output, enforce=False)
