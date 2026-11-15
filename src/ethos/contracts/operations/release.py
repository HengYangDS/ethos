"""The `ethos release` command: the releasing host accepts the release it installed."""

from pathlib import Path

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes


class AcceptRequest(CommandRequest):
    """Accept the release that the invoking installation is, bound to its checksum file."""

    checksums: Path = described(..., "The release's `SHA256SUMS` file.")
    apply: Apply = False


ACCEPT = Command(
    name="release accept",
    summary="Accept the installed release as this repository's accepted release identity.",
    request=AcceptRequest,
    operations=modes(
        "release.accept",
        "Report whether the installed release can be accepted.",
        "Store the installed release's wheel and record its accepted identity once.",
        request="checksums",
    ),
)
