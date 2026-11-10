"""The `ethos lane handoff` requests and their operations.

A handoff moves a Work Lane to another holder: `transfer` moves one exact local Lease generation,
and across hosts `export` packages the lane's Git and context state, `import` creates the
destination's coordination from a verified package, and `revoke-source` revokes the source Lease
once the destination acknowledged it.
"""

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import ExpectHead
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.lease import BRANCH
from ethos.contracts.operations.lease import DAY
from ethos.contracts.operations.lease import EXPIRES_AT
from ethos.contracts.operations.lease import GENERATION
from ethos.contracts.operations.lease import HOLDER
from ethos.contracts.operations.lease import TARGET
from ethos.contracts.operations.lease import TTL

_LEASE = "generation expires_at branch holder_ref target_holder_ref"
_PACKAGE = "The handoff package directory."


class TransferRequest(CommandRequest):
    """Transfer one exact local Lease generation to a new holder."""

    generation: int = described(..., GENERATION)
    expires_at: str = described(..., EXPIRES_AT)
    branch: str = described(..., BRANCH)
    holder_ref: str = described(..., HOLDER)
    target_holder_ref: str = described(..., TARGET)
    ttl_seconds: int = described(DAY, TTL)
    apply: Apply = False


class ExportRequest(CommandRequest):
    """Export content-addressed Git and context state for another common directory."""

    generation: int = described(..., GENERATION)
    expires_at: str = described(..., EXPIRES_AT)
    branch: str = described(..., BRANCH)
    holder_ref: str = described(..., HOLDER)
    target_holder_ref: str = described(..., TARGET)
    expect_head: ExpectHead
    context_text: str = described("", "The context the destination resumes from.")
    context_file: str | None = described(None, "A file holding that context instead.")
    output_root: str | None = described(None, "Where the package is written.")
    apply: Apply = False


class ImportRequest(CommandRequest):
    """Import a verified package and create destination-local coordination."""

    package: str = described(..., _PACKAGE)
    target_holder_ref: str = described(..., "The destination's holder, as the package names it.")
    apply: Apply = False


class RevokeSourceRequest(CommandRequest):
    """Revoke the exact source Lease after destination acknowledgement."""

    generation: int = described(..., GENERATION)
    expires_at: str = described(..., EXPIRES_AT)
    package: str = described(..., _PACKAGE)
    acknowledgement: str = described(..., "The destination's acknowledgement of the package.")
    holder_ref: str = described(..., HOLDER)
    expect_head: ExpectHead
    apply: Apply = False


TRANSFER = Command(
    name="lane handoff transfer",
    summary="Transfer one exact local Lease generation to a new holder.",
    request=TransferRequest,
    operations=modes(
        "lane.handoff.transfer",
        "Report whether the Lease generation can move to the target holder.",
        "Move the Lease generation to the target holder by exact compare.",
        request=f"{_LEASE} ttl_seconds",
        preview_exit="verdict",
    ),
)
EXPORT = Command(
    name="lane handoff export",
    summary="Export content-addressed Git/context state for another common directory.",
    request=ExportRequest,
    operations=modes(
        "lane.handoff.export",
        "Report whether the clean lane at the expected head can be packaged for the target.",
        "Write the content-addressed package of the lane's Git and context state.",
        request=f"{_LEASE} expect_head context_text context_file output_root",
        preview_exit="verdict",
    ),
)
IMPORT = Command(
    name="lane handoff import",
    summary="Import a verified package and create destination-local coordination.",
    request=ImportRequest,
    operations=modes(
        "lane.handoff.import",
        "Verify the package and report the coordination its import would create.",
        "Create the lane's ref, worktree and Lease from the package, and acknowledge it.",
        request="package target_holder_ref",
        preview_exit="verdict",
        writes="local-write host-write",
    ),
)
REVOKE_SOURCE = Command(
    name="lane handoff revoke-source",
    summary="Revoke the exact source Lease after destination acknowledgement.",
    request=RevokeSourceRequest,
    operations=modes(
        "lane.handoff.revoke-source",
        "Report whether the destination's acknowledgement admits revoking the source Lease.",
        "Revoke the source Lease by exact compare.",
        request="generation expires_at package acknowledgement holder_ref expect_head",
        destructive=True,
        preview_exit="verdict",
    ),
)
HANDOFF = (TRANSFER, EXPORT, IMPORT, REVOKE_SOURCE)
