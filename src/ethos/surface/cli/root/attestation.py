"""Public record and query projections over the sole Attestation set."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated
from typing import cast

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import validate_attestation_selector
from ethos.result import EthosResult
from ethos.surface.cli.application import app as root_app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_app = App(
    name="attestation",
    help="Record or query the sole Git-native Attestation set.",
)
root_app.command(_app)


def _input_attestation(path: Path) -> Attestation:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        message = "attestation_input_object_required"
        raise TypeError(message)
    if "id" in payload:
        return Attestation.model_validate_json(raw)
    attestation = Attestation.issue(payload)
    if raw != attestation.canonical_json(exclude_id=True).encode():
        message = "semantic_json_noncanonical"
        raise ValueError(message)
    return attestation


def _input_failure(command: str, error: Exception) -> EthosResult:
    code = str(error) or "attestation_input_invalid"
    return EthosResult(
        command=command,
        verdict="block",
        state="gapped",
        required_gaps=(code,),
        next_action="provide one canonical Attestation v2 JSON input",
        data={"error_boundary": "attestation_input"},
    )


@_app.command
def record(
    input_path: Annotated[str, Parameter(name="--input")],
    *,
    root: RootOption | None = None,
    apply: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Validate or issue one Attestation, then exact-CAS union it when applied."""
    command = "attestation record"
    repo = resolve_root(root)
    try:
        attestation = _input_attestation(Path(input_path))
        if apply:
            result = record_attestations(repo, (attestation,))
            set_root = str(result["root"])
            added = cast("tuple[str, ...]", result["added"])
            state = "recorded" if added else "unchanged"
        else:
            current_root, current = read_attestation_set(repo)
            present = any(item.id == attestation.id for item in current)
            set_root = current_root
            added = () if present else (attestation.id,)
            state = "unchanged" if present else "ready"
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        emit(_input_failure(command, error), json_output=json_output)
        return
    emit(
        EthosResult(
            command=command,
            verdict="pass",
            state=state,
            data={
                "apply": apply,
                "set_root": set_root,
                "added": list(added),
                "attestation": attestation.model_dump(mode="json"),
                "authorizes_effects": False,
            },
        ),
        json_output=json_output,
        artifact_root=repo,
    )


@_app.command
def query(
    *,
    root: RootOption | None = None,
    identity: Annotated[str, Parameter(name="--id")] = "",
    predicate: str = "",
    verifier: str = "",
    subject: str = "",
    payload_kind: Annotated[str, Parameter(name="--payload-kind")] = "",
    json_output: JsonFlag = False,
) -> None:
    """Return exact matching Attestations without claiming effect authority."""
    command = "attestation query"
    repo = resolve_root(root)
    try:
        identity = validate_attestation_selector("id", identity)
        predicate = validate_attestation_selector("predicate", predicate)
        verifier = validate_attestation_selector("verifier", verifier)
        subject = validate_attestation_selector("subject", subject)
        payload_kind = validate_attestation_selector("payload_kind", payload_kind)
        root_identity, members = read_attestation_set(repo)
    except ValueError as error:
        emit(_input_failure(command, error), json_output=json_output)
        return
    selected = tuple(
        item
        for item in members
        if (not identity or item.id == identity)
        and (not predicate or item.predicate == predicate)
        and (not verifier or item.verifier == verifier)
        and (not subject or item.subject == subject)
        and (not payload_kind or item.payload.kind == payload_kind)
    )
    emit(
        EthosResult(
            command=command,
            verdict="pass",
            state="observed",
            summary={"match_count": len(selected)},
            data={
                "set_root": root_identity,
                "attestations": [item.model_dump(mode="json") for item in selected],
                "authorizes_effects": False,
            },
        ),
        json_output=json_output,
        artifact_root=repo,
    )
