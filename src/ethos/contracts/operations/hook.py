"""The `ethos hook` requests and their operations: hook-time reports, installation, retirement.

A report reads the repository and keeps evidence only. `hook install` writes without a token, a
named exemption that A8 owns; its `--reset-state` mode is authorized and destructive.
"""

from typing import Literal

from ethos.contracts.operations.declaration import Apply
from ethos.contracts.operations.declaration import Authorize
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Operation
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import modes
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch

_REPORT = "read local-evidence-write"
_INSTALL = f"{_REPORT} local-write host-write"
_PLAN = "The digest of the previewed plan to apply."


def _report(identity: str, summary: str, request: str) -> tuple[Operation]:
    """Declare a command's one operation: a report that exits by its verdict."""
    return (
        operation(
            identity, summary, select="", request=request, effects=_REPORT, exit_kind="verdict"
        ),
    )


class AdmitRequest(CommandRequest):
    """Ask whether a host may go on at one hook layer before it mutates tracked files."""

    layer: str = described(..., "The hook layer: context, pre-tool, pre-run, post-write, git, ci.")
    paths: tuple[str, ...] = described((), "The paths the host would write, relative to the root.")
    command: str = described("", "The shell command that a `pre-run` host would run.")
    editor_root: str | None = described(None, "The worktree that the editor writes in.")
    expected_root: str | None = described(None, "The root that a `context` host expects.")
    require_editor_root: bool = switch("Refuse a write unless the editor root is the bound root.")


class CommitRangeRequest(CommandRequest):
    """Name one exact introduced range and the check to run over it."""

    target_ref: str = described(..., "The full ref that the push updates.")
    proposed_head: str = described(..., "The object that the ref would point at.")
    remote_head: str = described(..., "The object that the remote's ref points at, or zero.")
    remote: str = described(..., "The name of the remote that the push goes to.")
    trusted_baseline: str = described("", "The commit whose policy judges a new ref's range.")
    check: Literal["policy", "peer-identity"] = described(
        "policy", "Check the commit policy, or the identity of a protected peer in CI."
    )


class RefUpdateRequest(CommandRequest):
    """Name one exact ref update that detached CI observes."""

    target_ref: str = described(..., "The full ref that the push updates.")
    proposed_head: str = described(..., "The object that the ref would point at.")
    remote_head: str = described(..., "The object that the remote's ref points at, or zero.")
    remote: str = described(..., "The name of the remote that the push goes to.")
    trusted_baseline: str = described("", "The commit whose policy judges a new ref's range.")


class RefTransactionRequest(CommandRequest):
    """Name one local ref update that Git's reference-transaction hook is about to commit."""

    ref_name: str = described(..., "The full ref that the transaction moves.")
    old_value: str = described(..., "The object that the ref points at, or zero.")
    new_value: str = described(..., "The object that the ref would point at, or zero.")
    phase: str = described("prepared", "The transaction phase that the hook runs in.")


class InstallRequest(CommandRequest):
    """Activate one hook runtime for the repository family, resetting its state if asked."""

    installed_runtime: str | None = described(None, "An installed ETHOS runtime to activate.")
    reset_state: bool = switch("Reset local state whose schema cannot migrate; needs authorizing.")
    authorize: Authorize = False


class RetireSupplyRequest(CommandRequest):
    """Preview, or retire, host installations pinned before their consumers were recorded."""

    scan: tuple[str, ...] = described((), "A root of repositories that may name an installation.")
    expect_plan: str = described("", _PLAN)
    grace_days: int = described(7, "The days an installation stays after it last changed.")
    apply: Apply = False
    authorize: Authorize = False


class RetireRecordsRequest(CommandRequest):
    """Preview which Git-common store records may retire, or apply an approved plan."""

    expect_plan: str = described("", _PLAN)
    apply: Apply = False
    authorize: Authorize = False


ADMIT = Command(
    name="hook admit",
    summary="Evaluate hook-time write admission before a host mutates tracked files.",
    request=AdmitRequest,
    positionals=("layer", "paths"),
    operations=_report(
        "hook.admit",
        "Report whether the host may go on at its layer.",
        "layer paths command editor_root expected_root require_editor_root",
    ),
)
COMMIT_RANGE = Command(
    name="hook commit-range",
    summary="Evaluate commit policy over one exact range, or check it for a protected peer.",
    request=CommitRangeRequest,
    operations=_report(
        "hook.commit-range",
        "Report what the range introduces under the selected check.",
        "target_ref proposed_head remote_head remote trusted_baseline check",
    ),
)
REF_UPDATE = Command(
    name="hook ref-update",
    summary="Observe exact ref-role, introduced-range and OpenSpec obligations without host state.",
    request=RefUpdateRequest,
    operations=_report(
        "hook.ref-update",
        "Report the obligations of one ref update.",
        "target_ref proposed_head remote_head remote trusted_baseline",
    ),
)
REF_TRANSACTION = Command(
    name="hook ref-transaction",
    summary="Evaluate a local ref update before Git commits it to the ref store.",
    request=RefTransactionRequest,
    positionals=("ref_name", "old_value", "new_value"),
    operations=_report(
        "hook.ref-transaction",
        "Report whether the ref may move; an accepted branch moves only through landing.",
        "ref_name old_value new_value phase",
    ),
)
INSTALL = Command(
    name="hook install",
    summary="Converge the repository-family hook runtime through Git-common activation.",
    request=InstallRequest,
    spellings=(("installed_runtime", "runtime"),),
    operations=(
        operation(
            "hook.install",
            "Install and activate the hook runtime.",
            select="reset_state=false",
            request="installed_runtime",
            effects=_INSTALL,
            exit_kind="verdict",
        ),
        operation(
            "hook.install.reset-state",
            "Reset the local state whose schema cannot migrate, then install the hook runtime.",
            select="reset_state=true",
            request="installed_runtime authorize",
            effects=_INSTALL,
            authorization="authorize",
            destructive=True,
            exit_kind="verdict",
        ),
    ),
)
RETIRE_SUPPLY = Command(
    name="hook retire-supply",
    summary="Preview host installations pinned before consumers were recorded; retire a plan.",
    request=RetireSupplyRequest,
    operations=modes(
        "hook.retire-supply",
        "Plan the retirement of the installations that nothing scanned still needs.",
        "Retire exactly the planned installations, recording each consumer that names one.",
        request="scan expect_plan grace_days",
        authorization="authorize",
        destructive=True,
        preview_exit="verdict",
        writes="local-write host-write",
    ),
)
RETIRE_RECORDS = Command(
    name="hook retire-records",
    summary="Preview which store records may retire and write the plan; apply an approved plan.",
    request=RetireRecordsRequest,
    operations=modes(
        "hook.retire-records",
        "Plan the retirement of every owned, unnamed record older than its floor.",
        "Delete the planned records that a fresh scan still selects, and receipt the run.",
        request="expect_plan",
        authorization="authorize",
        destructive=True,
        preview_exit="verdict",
    ),
)
HOOK = (ADMIT, COMMIT_RANGE, REF_UPDATE, REF_TRANSACTION, INSTALL, RETIRE_SUPPLY, RETIRE_RECORDS)
