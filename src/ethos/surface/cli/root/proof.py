"""Render the shared proof operation through Cyclopts."""

from typing import Annotated

from cyclopts import Parameter

from ethos.application.proof.operation import ProofRequest
from ethos.application.proof.operation import prove_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_DEFAULT_REQUEST = ProofRequest()


@app.command
def prove(
    options: Annotated[ProofRequest, Parameter(name="*")] = _DEFAULT_REQUEST,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Produce proof readiness or one executed generic proof Attestation."""
    emit(prove_repository(resolve_root(root), options), json_output=json_output)
