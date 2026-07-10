"""No-compatibility-residue quality command registration."""

from __future__ import annotations

from typing import cast

from ethos.repository.policy.no_compat.core import no_compat_report
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.result import EthosResult


def no_compat(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check production source for compatibility residue."""
    repo = resolve_root(root)
    report = no_compat_report(repo)
    result = EthosResult(
        command="quality no-compat",
        ok=bool(report["ok"]),
        state=str(report["state"]),
        summary=cast("dict[str, object]", report["summary"]),
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output)
