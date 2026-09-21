"""Render the shared integration operation through Cyclopts."""

from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from ethos.domain.land.operation import land_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@dataclass(frozen=True, slots=True)
class _LandOptions:
    """CLI options for `ethos land`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    candidate_head: Annotated[str | None, Parameter(name="--candidate-head")] = None
    closeout: bool = False
    release: bool = False
    release_head: Annotated[str, Parameter(name="--release-head")] = ""
    tag: str = ""
    independent_verification_receipt: Annotated[
        Path | None, Parameter(name="--independent-verification-receipt")
    ] = None


_DEFAULT_LAND_OPTIONS = _LandOptions()


@app.command
def land(
    options: Annotated[_LandOptions, Parameter(name="*")] = _DEFAULT_LAND_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report land readiness."""
    emit(
        land_repository(resolve_root(root), **asdict(options)),
        json_output=json_output,
        enforce=options.apply,
    )
