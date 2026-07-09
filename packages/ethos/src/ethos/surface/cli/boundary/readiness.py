"""Readiness quality command registrations."""

from __future__ import annotations

from typing import cast

from ethos.domain.readiness.enterprise import enterprise_readiness_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import quality_app
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


@quality_app.command(name="enterprise-readiness")
def enterprise_readiness(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Audit enterprise-neutral readiness across product boundary, docs, identity, and release."""
    repo = resolve_root(root)
    report = enterprise_readiness_report(repo)
    result = EthosResult(
        command="quality enterprise-readiness",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=dict(cast("dict[str, object]", report["summary"])),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=(
            (
                "resolve enterprise-readiness required gaps, then rerun "
                "ethos quality enterprise-readiness --json"
            )
            if report["required_gaps"]
            else "ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
        ),
        data=report,
    )
    emit(result, json_output=json_output)
