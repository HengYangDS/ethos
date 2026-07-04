"""Fleet command group — external adopter inspection.

A surface command module: binds args, calls the domain/repository report, emits.
Registers onto the shared fleet_app from _base (import side-effect); cli.py imports
this module so the decorator runs. Imports only what this group needs.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs the runtime type for --target

from ethos.repository.adoption.fleet import inspect_adopter
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import fleet_app
from ethos_core.result import EthosResult


@fleet_app.command(name="inspect")
def fleet_inspect(
    *,
    target: Path,
    json_output: JsonFlag = False,
) -> None:
    """Inspect an external repository as an ETHOS adopter."""
    report = inspect_adopter(target)
    result = EthosResult(
        command="fleet inspect",
        ok=bool(report["ok"]),
        state="ready" if report["ok"] else "gapped",
        required_gaps=tuple(report["required_gaps"]),
        data=report,
    )
    emit(result, json_output, enforce=False)
