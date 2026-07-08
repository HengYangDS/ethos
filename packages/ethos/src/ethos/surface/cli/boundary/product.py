"""Quality boundary command registrations."""

from __future__ import annotations

from typing import cast

from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import quality_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def _emit_policy_report(
    *,
    command: str,
    report: dict[str, object],
    next_action: str,
    json_output: bool,
) -> None:
    result = EthosResult(
        command=command,
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=cast("dict[str, object]", report["summary"]),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=(next_action,),
        data=report,
    )
    emit(result, json_output=json_output)


@quality_app.command(name="product-boundary")
def product_boundary(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Audit active product surfaces for author, path, adopter, and phase leakage."""
    _emit_policy_report(
        command="quality product-boundary",
        report=product_boundary_report(resolve_root(root)),
        next_action="neutralize active product surfaces; leave historical evidence classified",
        json_output=json_output,
    )


@quality_app.command(name="contributor-policy")
def contributor_policy(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
    """Audit organization-native contributor, role, and automation identity policy."""
    _emit_policy_report(
        command="quality contributor-policy",
        report=contributor_policy_report(resolve_root(root)),
        next_action="declare role-based humans, teams, and automation identities",
        json_output=json_output,
    )
