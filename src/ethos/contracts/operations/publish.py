"""The `ethos publish` request and the five publication operations its selectors choose between."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch


class PublishRequest(CommandRequest):
    """One publication request: readiness, a derived request for exact refs, or its receipt."""

    apply: bool = switch("Apply the receipt's request to its peers.")
    authorize: bool = switch("Authorize the apply.")
    expect_head: str | None = described(None, "The head the publication expects.")
    probe_remote: bool = switch("Probe the declared peers' current refs.")
    target_refs: tuple[str, ...] = described((), "Publish this full ref; repeat for more.")
    peer_ids: tuple[str, ...] = described(
        (), "Publish only to this declared peer, not to every peer; repeat for more."
    )
    receipt: str | None = described(None, "The derived publication request to apply.")
    receipt_sha256: str | None = described(None, "The SHA-256 of that request.")
    retire: bool = switch("Retire the refs from the peers instead of publishing them.")


_PROBED = "read remote-read local-evidence-write"
_APPLIED = "read remote-read local-evidence-write remote-write"

COMMAND = Command(
    name="publish",
    summary="Report readiness or project one exact publication operation.",
    request=PublishRequest,
    spellings=(("target_refs", "ref"), ("peer_ids", "peer")),
    operations=(
        operation(
            "publish.readiness",
            "Report local publication readiness.",
            select="target_refs=unset receipt=unset retire=false apply=false",
            request="expect_head probe_remote",
            effects="read remote-read",
        ),
        operation(
            "publish.probe",
            "Derive the exact publication request of each ref from the live peers.",
            select="target_refs=set receipt=unset retire=false apply=false",
            request="peer_ids probe_remote expect_head",
            effects=_PROBED,
            exit_kind="verdict",
        ),
        operation(
            "publish.apply",
            "Apply a derived publication request to its peers.",
            select="receipt=set retire=false apply=true",
            request="receipt_sha256 authorize expect_head",
            effects=_APPLIED,
            authorization="authorize",
            exit_kind="verdict",
        ),
        operation(
            "publish.retire.probe",
            "Derive the exact retirement request of each ref from the live peers.",
            select="retire=true target_refs=set receipt=unset apply=false",
            request="peer_ids probe_remote expect_head",
            effects=_PROBED,
            exit_kind="verdict",
        ),
        operation(
            "publish.retire.apply",
            "Retire the refs a derived retirement request names from its peers.",
            select="retire=true receipt=set apply=true",
            request="receipt_sha256 authorize expect_head",
            effects=_APPLIED,
            authorization="authorize",
            destructive=True,
            exit_kind="verdict",
        ),
    ),
)
