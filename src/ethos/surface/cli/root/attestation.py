"""Public record and query projections over the sole Attestation set."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Annotated
from typing import cast

from cyclopts import App
from cyclopts import Parameter

from ethos.adapters.repo.attestation_set import MEMBER_BYTES_LIMIT
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.attestation_set import release_attestation
from ethos.adapters.store.custody import custody_digests
from ethos.adapters.store.custody import require_custody
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


def _require_bounded(attestation: Attestation) -> None:
    """Refuse a new member above the set bound; the writer applies the same rule on apply."""
    if len(attestation.canonical_json().encode()) > MEMBER_BYTES_LIMIT:
        message = f"attestation_member_too_large:{attestation.id}"
        raise ValueError(message)


_NEXT_ACTIONS = {
    "attestation_member_too_large": (
        "store file bytes with --evidence and bind them as custody:sha256:<digest>"
    ),
    "attestation_release_actor_unadmitted": (
        "release as the member's verifier, or name reviewed content with --review-content"
        " and --reason"
    ),
}


def _input_failure(command: str, error: Exception) -> EthosResult:
    code = str(error) or "attestation_input_invalid"
    return EthosResult(
        command=command,
        verdict="block",
        state="gapped",
        required_gaps=(code,),
        next_action=_NEXT_ACTIONS.get(
            code.split(":", 1)[0], "provide one canonical Attestation v2 JSON input"
        ),
        data={"error_boundary": "attestation_input"},
    )


def _supplied_evidence(
    repo: Path, attestation: Attestation, paths: tuple[str, ...]
) -> dict[str, bytes]:
    """Match supplied files to declared custody digests; each declared digest needs bytes."""
    declared = custody_digests(attestation)
    supplied = {
        hashlib.sha256(payload).hexdigest(): payload
        for payload in (Path(path).read_bytes() for path in paths)
    }
    for digest in supplied:
        if digest not in declared:
            message = f"attestation_custody_undeclared:{digest}"
            raise ValueError(message)
    require_custody(repo, (digest for digest in declared if digest not in supplied))
    return supplied


@_app.command
def record(
    input_path: Annotated[str, Parameter(name="--input")],
    *,
    evidence: Annotated[tuple[str, ...], Parameter(name="--evidence")] = (),
    root: RootOption | None = None,
    apply: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Validate or issue one Attestation with its custody evidence, then exact-CAS union it."""
    command = "attestation record"
    repo = resolve_root(root)
    try:
        attestation = _input_attestation(Path(input_path))
        supplied = _supplied_evidence(repo, attestation, evidence)
        if apply:
            result = record_attestations(repo, (attestation,), custody=tuple(supplied.values()))
            set_root = str(result["root"])
            previous_set_root = str(result["previous_root"])
            added = cast("tuple[str, ...]", result["added"])
            gaps = {key: result[key] for key in ("lifetime_gap", "custody_gap") if key in result}
            state = "recorded" if added else "unchanged"
        else:
            current_root, current = read_attestation_set(repo)
            present = any(item.id == attestation.id for item in current)
            if not present:
                _require_bounded(attestation)
            set_root = previous_set_root = current_root
            added = () if present else (attestation.id,)
            gaps = {}
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
                "previous_set_root": previous_set_root,
                "added": list(added),
                "attestation": attestation.model_dump(mode="json"),
                "custody": list(custody_digests(attestation)),
                **gaps,
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


@_app.command
def release(
    *,
    identity: Annotated[str, Parameter(name="--id")],
    reason: str = "",
    review_content: Annotated[bool, Parameter(name="--review-content")] = False,
    root: RootOption | None = None,
    apply: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Release one open-predicate member and its unbound custody bytes by exact CAS."""
    command = "attestation release"
    repo = resolve_root(root)
    try:
        identity = validate_attestation_selector("id", identity)
        result = release_attestation(
            repo,
            identity,
            actor=os.environ.get("ETHOS_ACTOR", "").strip(),
            review=reason if review_content else "",
            apply=apply,
        )
    except (OSError, ValueError) as error:
        emit(_input_failure(command, error), json_output=json_output)
        return
    emit(
        EthosResult(
            command=command,
            verdict="pass",
            state="released" if apply else "ready",
            data={
                **{
                    key: list(value) if isinstance(value, tuple) else value
                    for key, value in result.items()
                },
                "apply": apply,
                "authorizes_effects": False,
            },
        ),
        json_output=json_output,
        artifact_root=repo,
    )
