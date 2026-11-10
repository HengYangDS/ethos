"""The `ethos attestation` requests and their operations over the sole Attestation set."""

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Reason
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch


class RecordRequest(CommandRequest):
    """Validate one canonical Attestation, or union it into the set."""

    input_path: str = described(..., "The canonical Attestation v2 JSON input file.")
    evidence: tuple[str, ...] = described(
        (), "A file of custody bytes that a declared digest names; repeat for more."
    )
    apply: Apply = False


class QueryRequest(CommandRequest):
    """Select the members that match every given selector exactly."""

    identity: str = described("", "Match this Attestation ID.")
    predicate: str = described("", "Match this predicate.")
    verifier: str = described("", "Match this verifier.")
    subject: str = described("", "Match this subject.")
    payload_kind: str = described("", "Match this payload kind.")


class ReleaseRequest(CommandRequest):
    """Release one open-predicate member and its unbound custody bytes."""

    identity: str = described(..., "The ID of the member to release.")
    reason: Reason = ""
    review_content: bool = switch("Release another verifier's member as reviewed, with a reason.")
    apply: Apply = False


RECORD = Command(
    name="attestation record",
    summary="Validate or issue one Attestation with its custody evidence, then exact-CAS union it.",
    request=RecordRequest,
    spellings=(("input_path", "input"),),
    positionals=("input_path",),
    operations=modes(
        "attestation.record",
        "Validate one Attestation and report the union it would make.",
        "Union one Attestation into the sole set by exact compare-and-swap.",
        request="input_path evidence",
        preview_exit="verdict",
    ),
)
QUERY = Command(
    name="attestation query",
    summary="Return exact matching Attestations without claiming effect authority.",
    request=QueryRequest,
    spellings=(("identity", "id"),),
    operations=(
        operation(
            "attestation.query",
            "Return the Attestations that match every given selector.",
            select="",
            request="identity predicate verifier subject payload_kind",
            effects="read local-evidence-write",
            exit_kind="verdict",
        ),
    ),
)
RELEASE = Command(
    name="attestation release",
    summary="Release one open-predicate member and its unbound custody bytes by exact CAS.",
    request=ReleaseRequest,
    spellings=(("identity", "id"),),
    operations=modes(
        "attestation.release",
        "Report whether one member can be released.",
        "Release one member and its unbound custody bytes by exact compare-and-swap.",
        request="identity reason review_content",
        destructive=True,
        preview_exit="verdict",
    ),
)
ATTESTATION = (RECORD, QUERY, RELEASE)
