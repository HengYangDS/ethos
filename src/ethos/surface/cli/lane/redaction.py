"""Redact protected peer identity in a Work Lane's records, or verify a redaction."""

import sys
from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

from ethos.application.redaction import redact_private_addresses
from ethos.surface.cli.lane.lifecycle import lane_app
from ethos.surface.cli.lane.lifecycle import project_lane_result
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root

_app = App(name="redact", help="Redact protected peer identity in a lane's records.")
lane_app.command(_app)
# A key is 64 hex characters and at most one newline; anything longer is refused unread.
_KEY_BYTES = 66


@_app.command(name="private-addresses")
def lane_redact_private_addresses(
    *,
    apply: bool = False,
    verify: bool = False,
    key_stdin: Annotated[bool, Parameter(name="--key-stdin")] = False,
    authorize: bool = False,
    expect_head: Annotated[str, Parameter(name="--expect-head")] = "",
    base: Annotated[str, Parameter(name="--base")] = "",
    head: Annotated[str, Parameter(name="--head")] = "",
    rotate: bool = False,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Preview the occurrences without a key; apply or verify with the key on standard input."""
    key = sys.stdin.read(_KEY_BYTES + 1) if key_stdin else ""
    report = redact_private_addresses(
        resolve_root(root),
        apply=apply,
        verify=verify,
        key=key,
        authorize=authorize,
        expect_head=expect_head,
        base=base,
        head=head,
        rotate=rotate,
    )
    project_lane_result(
        "lane redact private-addresses",
        report,
        enforce=apply or verify,
        json_output=json_output,
        summary={
            key_name: report[key_name]
            for key_name in ("count", "outside_roots", "changed_paths", "generation")
            if key_name in report
        },
    )
