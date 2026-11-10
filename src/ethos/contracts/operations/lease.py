"""The `ethos lane lease` requests and their operations.

A Lane Lease binds one Work Lane to its holder by four coordinates: the branch, the holder, the
generation and its expiry. `renew` and `resume` advance an exact generation, `reacquire` creates
missing coordination without touching retained content, and `takeover` moves a Lease to another
holder under an accepted Attestation, which every takeover's argv carries.
"""

from dataclasses import replace
from pathlib import Path
from typing import Literal

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Authorize
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import ExpectHead
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.declaration import switch

# The four coordinates, the target holder and the next generation's lifetime, wherever they recur.
GENERATION = "The Lease generation that the holder saw."
EXPIRES_AT = "The expiry of that generation."
BRANCH = "The Work Lane's branch."
HOLDER = "The holder of that generation, such as `agent:<id>`."
TARGET = "The holder the Lease moves to."
TTL = "How long the next generation lasts, in seconds."
DAY = 86_400
_CURRENT = "generation expires_at branch holder_ref ttl_seconds"


class RenewRequest(CommandRequest):
    """Renew an unexpired Lease generation; a preview without its coordinates reads them."""

    generation: int | None = described(None, GENERATION)
    expires_at: str | None = described(None, EXPIRES_AT)
    branch: str | None = described(None, BRANCH)
    holder_ref: str | None = described(None, HOLDER)
    ttl_seconds: int = described(DAY, TTL)
    apply: Apply = False


class ResumeRequest(CommandRequest):
    """Resume an expired Lease for the same holder and generation; a preview reads it."""

    generation: int | None = described(None, GENERATION)
    expires_at: str | None = described(None, EXPIRES_AT)
    branch: str | None = described(None, BRANCH)
    holder_ref: str | None = described(None, HOLDER)
    ttl_seconds: int = described(DAY, TTL)
    contrary_decision: bool = switch("A decision contrary to resuming is present.")
    apply: Apply = False


class ReacquireRequest(CommandRequest):
    """Derive or acquire missing coordination without changing retained content."""

    path: Path = described(..., "The Work Lane's worktree.")
    holder_ref: str = described(..., "The holder to acquire the Lease for.")
    expect_head: ExpectHead = None
    expect_snapshot: str = described("", "The coordinates' digest that the preview reported.")
    expires_at: str = described("", "The expiry that the preview reported.")
    apply: Apply = False
    authorize: Authorize = False


class TakeoverRequest(CommandRequest):
    """Move one Lease to another holder under an accepted authorization."""

    branch: str = described(..., BRANCH)
    source_holder_ref: str = described(..., "The holder the Lease moves from.")
    target_holder_ref: str = described(..., TARGET)
    generation: int = described(..., GENERATION)
    expires_at: str = described(..., EXPIRES_AT)
    source_state: Literal["quiesced", "source_lost"] = described(..., "The source's end state.")
    authorization: Path = described(..., "The accepted Attestation that authorizes the takeover.")
    ttl_seconds: int = described(DAY, TTL)
    apply: Apply = False


RENEW = Command(
    name="lane lease renew",
    summary="Renew one exact unexpired local Lease generation; a preview reads the current one.",
    request=RenewRequest,
    operations=modes(
        "lane.lease.renew",
        "Report the renewal of the given or current Lease and the request that applies it.",
        "Renew the Lease by exact compare of its four coordinates.",
        request=_CURRENT,
        preview_exit="verdict",
    ),
)
RESUME = Command(
    name="lane lease resume",
    summary="Resume an expired Lease for the same holder and generation; a preview reads it.",
    request=ResumeRequest,
    spellings=(("contrary_decision", "contrary-decision-present"),),
    operations=modes(
        "lane.lease.resume",
        "Report the resumption of the given or current Lease and the request that applies it.",
        "Resume the expired Lease by exact compare of its four coordinates.",
        request=f"{_CURRENT} contrary_decision",
        preview_exit="verdict",
    ),
)
REACQUIRE = Command(
    name="lane lease reacquire",
    summary="Derive or acquire missing coordination without changing retained content.",
    request=ReacquireRequest,
    operations=modes(
        "lane.lease.reacquire",
        "Derive the missing Lease's coordinates and the exact request that acquires it.",
        "Acquire the Lease at the derived coordinates and record its Attestation.",
        request="path holder_ref expect_head expect_snapshot expires_at",
        authorization="authorize",
        preview_exit="verdict",
    ),
)
TAKEOVER = Command(
    name="lane lease takeover",
    summary="Apply one accepted exact-CAS Lease takeover.",
    request=TakeoverRequest,
    operations=tuple(
        replace(item, authorization="attestation")
        for item in modes(
            "lane.lease.takeover",
            "Report whether the accepted authorization admits the takeover.",
            "Move the Lease to the target holder by exact compare and record its Attestation.",
            request=(
                "branch source_holder_ref target_holder_ref generation expires_at source_state"
                " authorization ttl_seconds"
            ),
            preview_exit="verdict",
        )
    ),
)
LEASE = (RENEW, RESUME, REACQUIRE, TAKEOVER)
