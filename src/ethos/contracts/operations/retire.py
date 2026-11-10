"""The `ethos lane retire` requests and their operations.

A Work Lane retires once accepted truth or a successor absorbed it, an unlinked topic ref once
accepted truth absorbed it, and divergent history or reviewed content by an abandonment that a
person reviews through its immutable receipt, which `recover` resumes after a partial run. Each
apply deletes only what its preview or receipt bound.
"""

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Authorize
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import ExpectHead
from ethos.contracts.operations.declaration import Reason
from ethos.contracts.operations.declaration import Receipt
from ethos.contracts.operations.declaration import ReceiptSha256
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.declaration import switch

_BRANCH = "The branch to retire."


class SupersededRequest(CommandRequest):
    """Retire a lane its successor absorbed, or derive the receipt that retains its history."""

    branch: str | None = described(None, _BRANCH)
    path: str | None = described(None, "The lane's worktree.")
    expect_head: ExpectHead = None
    absorbed_by: str = described("", "Accepted/successor OID, or refs/heads/<topic> to retain.")
    reason: Reason = ""
    apply: Apply = False
    authorize: Authorize = False


class LandedRequest(CommandRequest):
    """Retire an explicitly selected clean topic worktree absorbed by accepted truth."""

    branch: str | None = described(None, _BRANCH)
    expect_head: ExpectHead = None
    apply: Apply = False
    authorize: Authorize = False


class AbsorbedRefRequest(CommandRequest):
    """Retire one exact unlinked, unleased local topic ref absorbed by accepted truth."""

    branch: str = described(..., _BRANCH)
    expect_head: ExpectHead
    accepted_head: str = described(..., "The accepted head that absorbed the ref.")
    apply: Apply = False
    authorize: Authorize = False
    confirm_irreversible: bool = switch("Confirm that deleting the ref cannot be undone.")


class AbandonRequest(CommandRequest):
    """Derive the abandonment of divergent history or reviewed content, or apply its receipt."""

    branch: str | None = described(None, _BRANCH)
    path: str = described("", "A detached worktree to review instead of a branch.")
    reason_code: str = described("", "The reason's code, such as `content-review`.")
    reason: Reason = ""
    review_content: bool = switch("Inventory content and index for review before retirement.")
    receipt: Receipt = None
    receipt_sha256: ReceiptSha256 = None
    apply: Apply = False
    authorize: Authorize = False


class RecoverRequest(CommandRequest):
    """Resume one exact partial retirement from its immutable receipt."""

    receipt: Receipt
    receipt_sha256: ReceiptSha256
    apply: Apply = False
    authorize: Authorize = False


SUPERSEDED = Command(
    name="lane retire superseded",
    summary="Retire absorbed work, or derive exact receipt-bound retained-topic retirement.",
    request=SupersededRequest,
    operations=modes(
        "lane.retire.superseded",
        "Report the retirement, or derive the receipt that retains the topic's history.",
        "Remove the lane's worktree, ref and Lease once its successor absorbed it.",
        request="branch path expect_head absorbed_by reason",
        authorization="authorize",
        destructive=True,
    ),
)
LANDED = Command(
    name="lane retire landed",
    summary="Retire an explicitly selected clean topic worktree absorbed by accepted truth.",
    request=LandedRequest,
    operations=modes(
        "lane.retire.landed",
        "Report the landed lanes and whether the selected one can retire.",
        "Remove the selected lane's worktree, ref and Lease at the expected head.",
        request="branch expect_head",
        authorization="authorize",
        destructive=True,
    ),
)
ABSORBED_REF = Command(
    name="lane retire absorbed-ref",
    summary="Retire one exact unlinked, unleased local topic ref absorbed by accepted truth.",
    request=AbsorbedRefRequest,
    operations=modes(
        "lane.retire.absorbed-ref",
        "Report whether accepted truth absorbed the ref and the exact deletion that applies it.",
        "Delete the ref at the expected head once its deletion is confirmed irreversible.",
        request="branch expect_head accepted_head",
        authorization="confirm-irreversible",
        destructive=True,
    ),
)
ABANDON = Command(
    name="lane retire abandon",
    summary="Derive or apply exact abandonment of divergent history or reviewed content.",
    request=AbandonRequest,
    operations=(
        *modes(
            "lane.retire.abandon",
            "Derive and keep the abandonment's receipt for a person to review.",
            "Refuse to abandon anything without the receipt that a derivation keeps.",
            select="receipt=unset",
            request="branch path reason_code reason review_content",
            authorization="authorize",
        ),
        *modes(
            "lane.retire.abandon.receipt",
            "Report what the receipt abandons and the effects that remain.",
            "Delete the worktree, ref and Lease that the receipt binds, or resume their deletion.",
            select="receipt=set",
            request="receipt_sha256",
            authorization="authorize",
            destructive=True,
        ),
    ),
)
RECOVER = Command(
    name="lane retire recover",
    summary="Resume one exact partial retirement from its immutable receipt.",
    request=RecoverRequest,
    operations=modes(
        "lane.retire.recover",
        "Report the receipt's completed and remaining effects.",
        "Take the receipt's remaining effects at the coordinates it binds.",
        request="receipt receipt_sha256",
        authorization="authorize",
        destructive=True,
    ),
)
RETIRE = (ABANDON, RECOVER, ABSORBED_REF, SUPERSEDED, LANDED)
