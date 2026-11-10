"""The `ethos lane` repair requests and their operations.

`project` and `format` regenerate declared native output and source formatting, `repair-paradigm`
repairs repository paradigm gaps, `trust-commit-signer` and `repair-signature` correct signing
authority and accepted history, and `redact private-addresses` redacts protected peer identity in
a lane's records. Each apply writes only what its preview reported.
"""

from pathlib import Path

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Authorize
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import ExpectHead
from ethos.contracts.operations.declaration import Reason
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch

_CHECK = "Report drift as a failure, writing nothing."
# A key is 64 hex characters and at most one newline; the CLI reads one character more, so a longer
# key is refused unread.
_KEY_CHARACTERS = 66
_REDACT = "key_stdin expect_head base head rotate"


class ProjectRequest(CommandRequest):
    """Generate every declared native projection, check it, or admit its previewed patch."""

    check: bool = switch(_CHECK)
    expect_head: ExpectHead = None
    patch: str | None = described(None, "The previewed patch file that an apply admits.")
    apply: Apply = False
    authorize: Authorize = False


class FormatRequest(CommandRequest):
    """Prepare the formatted sources, check them, or apply them after exact admission."""

    paths: tuple[str, ...] = described((), "The sources to format; none selects every source.")
    check: bool = switch(_CHECK)
    expect_head: ExpectHead = None
    apply: Apply = False
    authorize: Authorize = False


class RepairParadigmRequest(CommandRequest):
    """Plan, or apply, the deterministic repairs of the repository's paradigm gaps."""

    apply: Apply = False


class TrustCommitSignerRequest(CommandRequest):
    """Authorize Git's configured signer for one exact signed commit."""

    target_commit: str = described(..., "The signed commit whose signer to authorize.")
    expected_anchor_sha256: str = described(..., "The SHA-256 of the trust anchor it extends.")
    apply: Apply = False
    authorize: Authorize = False


class RepairSignatureRequest(CommandRequest):
    """Repair accepted signatures, or selected historical identities, keeping verified originals."""

    expect_head: ExpectHead
    replacement: str = described("", "The re-signed commit that replaces the accepted tip.")
    corrections: Path | None = described(None, "A JSON file of the identity corrections to make.")
    corrections_sha256: str = described("", "The SHA-256 of the corrections the preview read.")
    reason: Reason = ""
    backup: Path | None = described(None, "Where the verified originals are kept.")
    apply: Apply = False
    authorize: Authorize = False


class RedactRequest(CommandRequest):
    """Preview the protected peer occurrences, redact them, or verify a redaction."""

    key_stdin: bool = switch("Read the key from standard input.")
    expect_head: ExpectHead = None
    base: str = described("", "The revision a verify re-derives the redaction from.")
    head: str = described("", "The redacted revision that a verify checks.")
    rotate: bool = switch("Accept a key of another generation than the last recorded one.")
    verify: bool = switch("Verify a redaction and record its Attestation.")
    apply: Apply = False
    authorize: Authorize = False


PROJECT = Command(
    name="lane project",
    summary="Generate every declared native projection without requiring a product checkout.",
    request=ProjectRequest,
    operations=modes(
        "lane.project",
        "Report the projection patch, or with `--check` refuse its drift.",
        "Write the previewed projection patch after exact prewrite admission.",
        request="check expect_head patch",
        authorization="authorize",
        preview_exit="verdict",
    ),
)
FORMAT = Command(
    name="lane format",
    summary="Prepare all postimages without writes, or apply them after exact native admission.",
    request=FormatRequest,
    positionals=("paths",),
    operations=modes(
        "lane.format",
        "Report the formatted postimages, or with `--check` refuse their drift.",
        "Write the formatted postimages after exact prewrite admission.",
        request="paths check expect_head",
        authorization="authorize",
        preview_exit="verdict",
    ),
)
REPAIR_PARADIGM = Command(
    name="lane repair-paradigm",
    summary="Preview or apply the deterministic repairs of repository paradigm gaps.",
    request=RepairParadigmRequest,
    operations=modes(
        "lane.repair-paradigm",
        "Plan the repairs of the repository's paradigm gaps.",
        "Write the planned repairs after exact-path prewrite admission.",
        request="",
    ),
)
TRUST_COMMIT_SIGNER = Command(
    name="lane trust-commit-signer",
    summary="Authorize Git's configured signer for one exact signed commit.",
    request=TrustCommitSignerRequest,
    operations=modes(
        "lane.trust-commit-signer",
        "Report whether the signer verifies the commit and the anchor it would extend.",
        "Add the signer to the commit trust anchor by exact compare.",
        request="target_commit expected_anchor_sha256",
        authorization="authorize",
    ),
)
REPAIR_SIGNATURE = Command(
    name="lane repair-signature",
    summary="Repair accepted signatures or selected historical identities with verified originals.",
    request=RepairSignatureRequest,
    operations=modes(
        "lane.repair-signature",
        "Observe the repair, or recover a partial one, and name the request that applies it.",
        "Rewrite the accepted history as previewed, keeping the verified originals.",
        request="expect_head replacement corrections corrections_sha256 reason backup",
        authorization="authorize",
    ),
)
REDACT = Command(
    name="lane redact private-addresses",
    summary="Preview the occurrences without a key; apply or verify with the key on stdin.",
    request=RedactRequest,
    stdin_limit=_KEY_CHARACTERS + 1,
    stdin="key_stdin",
    operations=(
        *modes(
            "lane.redact.private-addresses",
            "List each occurrence's file, line and form, and whether it lies in the roots.",
            "Write markers and numbers in the effective roots under the lane's prewrite.",
            select="verify=false",
            request=_REDACT,
            authorization="authorize",
        ),
        operation(
            "lane.redact.private-addresses.verify",
            "Re-derive a head's markers and numbers from its base and record the Attestation.",
            select="verify=true apply=false",
            request=_REDACT,
            effects="read local-evidence-write local-write",
            authorization="apply",
            exit_kind="verdict",
        ),
    ),
)
LANE_REPAIR = (PROJECT, FORMAT, REPAIR_PARADIGM, TRUST_COMMIT_SIGNER, REPAIR_SIGNATURE, REDACT)
