"""Fleet commands for external adopter inspection and retirement readiness."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs the runtime type for --target
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.land.parity.core as land_parity
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.adoption.retirement.core import retirement_readiness_report
from ethos.repository.evidence.parity.core import parity_gaps_report
from ethos.repository.evidence.parity.core import shadow_parity_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import fleet_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def _parity_report(reporter, adopter: str, product_root: Path, target: Path) -> dict[str, object]:
    return reporter(
        adopter=adopter,
        root=product_root,
        target=target,
        current_target_head=git_adapter.current_tracked_head(target),
        current_product_head=git_adapter.current_tracked_head(product_root),
        acceptable_product_heads=land_parity.acceptable_parity_product_heads(product_root, adopter),
        acceptable_target_heads=land_parity.acceptable_parity_target_heads(
            product_root, target, adopter
        ),
    )


@fleet_app.command(name="inspect")
def fleet_inspect(*, target: Path, json_output: JsonFlag = False) -> None:
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
    emit(result, json_output=json_output, enforce=False)


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
        from ethos.adapters.shadow.core import run_shadow_parity

        shadow = run_shadow_parity(
            target=target,
            timeout_seconds=timeout_seconds,
            product_root=product_root,
        )
    else:
        shadow = _parity_report(shadow_parity_report, adopter, product_root, target)
    parity = _parity_report(parity_gaps_report, adopter, product_root, target)
    report = retirement_readiness_report(
        target=target,
        product_root=product_root,
        parity_gaps=parity,
        shadow=shadow,
    )
    required_gaps = cast("list[str]", report["required_gaps"])
    result = EthosResult(
        command="fleet retirement-readiness",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary={
            "adopter": report["adopter"],
            "gap_count": len(required_gaps),
        },
        required_gaps=tuple(required_gaps),
        next_actions=tuple(cast("list[str]", report["next_actions"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)
