"""Record, query and release members of the sole Git-native Attestation set.

Each operation takes the resolved repository root and its catalog request and returns one result;
none authorizes an effect, and an input the set refuses is a gapped result, not an exception.
"""

import hashlib
import json
from pathlib import Path
from typing import cast

from ethos.adapters.actor import process_actor
from ethos.adapters.repo.attestation_set import MEMBER_BYTES_LIMIT
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.attestation_set import release_attestation
from ethos.adapters.store.custody import custody_digests
from ethos.adapters.store.custody import require_custody
from ethos.contracts.operations.attestation import QueryRequest
from ethos.contracts.operations.attestation import RecordRequest
from ethos.contracts.operations.attestation import ReleaseRequest
from ethos.contracts.outcome import require
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import validate_attestation_selector
from ethos.result import EthosResult

_NEXT_ACTIONS = {
    "attestation_member_too_large": (
        "store file bytes with --evidence and bind them as custody:sha256:<digest>"
    ),
    "attestation_release_actor_unadmitted": (
        "release as the member's verifier, or name reviewed content with --review-content"
        " and --reason"
    ),
}


def _input_attestation(path: Path) -> Attestation:
    raw = path.read_bytes()
    payload = json.loads(raw)
    require(isinstance(payload, dict), "attestation_input_object_required")
    if "id" in payload:
        return Attestation.model_validate_json(raw)
    attestation = Attestation.issue(payload)
    canonical = attestation.canonical_json(exclude_id=True).encode()
    require(raw == canonical, "semantic_json_noncanonical")
    return attestation


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
        require(digest in declared, f"attestation_custody_undeclared:{digest}")
    require_custody(repo, (digest for digest in declared if digest not in supplied))
    return supplied


def record_attestation(root: Path, request: RecordRequest) -> EthosResult:
    """Validate or issue one Attestation with its custody evidence, then exact-CAS union it."""
    try:
        attestation = _input_attestation(Path(request.input_path))
        supplied = _supplied_evidence(root, attestation, request.evidence)
        if request.apply:
            result = record_attestations(root, (attestation,), custody=tuple(supplied.values()))
            set_root, previous_set_root = str(result["root"]), str(result["previous_root"])
            added = cast("tuple[str, ...]", result["added"])
            gaps = {key: result[key] for key in ("lifetime_gap", "custody_gap") if key in result}
            state = "recorded" if added else "unchanged"
        else:
            set_root, current = read_attestation_set(root)
            present = any(item.id == attestation.id for item in current)
            # The writer bounds a new member on apply; a preview refuses it the same way.
            bounded = len(attestation.canonical_json().encode()) <= MEMBER_BYTES_LIMIT
            require(present or bounded, f"attestation_member_too_large:{attestation.id}")
            previous_set_root, gaps = set_root, {}
            added = () if present else (attestation.id,)
            state = "unchanged" if present else "ready"
    except (OSError, TypeError, ValueError) as error:
        return _input_failure("attestation record", error)
    return EthosResult(
        command="attestation record",
        verdict="pass",
        state=state,
        data={
            "apply": request.apply,
            "set_root": set_root,
            "previous_set_root": previous_set_root,
            "added": list(added),
            "attestation": attestation.model_dump(mode="json"),
            "custody": list(custody_digests(attestation)),
            **gaps,
            "authorizes_effects": False,
        },
    )


def query_attestations(root: Path, request: QueryRequest) -> EthosResult:
    """Return exact matching Attestations without claiming effect authority."""
    try:
        identity = validate_attestation_selector("id", request.identity)
        predicate = validate_attestation_selector("predicate", request.predicate)
        verifier = validate_attestation_selector("verifier", request.verifier)
        subject = validate_attestation_selector("subject", request.subject)
        payload_kind = validate_attestation_selector("payload_kind", request.payload_kind)
        set_root, members = read_attestation_set(root)
    except ValueError as error:
        return _input_failure("attestation query", error)
    selected = tuple(
        item
        for item in members
        if (not identity or item.id == identity)
        and (not predicate or item.predicate == predicate)
        and (not verifier or item.verifier == verifier)
        and (not subject or item.subject == subject)
        and (not payload_kind or item.payload.kind == payload_kind)
    )
    return EthosResult(
        command="attestation query",
        verdict="pass",
        state="observed",
        summary={"match_count": len(selected)},
        data={
            "set_root": set_root,
            "attestations": [item.model_dump(mode="json") for item in selected],
            "authorizes_effects": False,
        },
    )


def release_attestation_member(root: Path, request: ReleaseRequest) -> EthosResult:
    """Release one open-predicate member and its unbound custody bytes by exact CAS."""
    try:
        result = release_attestation(
            root,
            validate_attestation_selector("id", request.identity),
            actor=process_actor(),
            review=request.reason if request.review_content else "",
            apply=request.apply,
        )
    except (OSError, ValueError) as error:
        return _input_failure("attestation release", error)
    return EthosResult(
        command="attestation release",
        verdict="pass",
        state="released" if request.apply else "ready",
        data={
            **{
                key: list(value) if isinstance(value, tuple) else value
                for key, value in result.items()
            },
            "apply": request.apply,
            "authorizes_effects": False,
        },
    )
