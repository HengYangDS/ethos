"""The `ethos land` request and the eight integration operations its selectors choose between."""

from pathlib import Path

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch
from ethos.contracts.proof.plan import AcceptancePurpose


class LandRequest(CommandRequest):
    """One integration request: candidate, accepted closeout, release or mapped re-tags."""

    apply: bool = switch("Apply the selected operation instead of previewing it.")
    authorize: bool = switch("Authorize the apply.")
    expect_head: str | None = described(
        None,
        "The head the operation expects: the lane head to land, the accepted head to close out, "
        "or the release source head.",
    )
    candidate_head: str | None = described(
        None,
        "The candidate head: the compare-and-swap target to land on, or what closeout audits.",
    )
    closeout: bool = switch("Advance the accepted branch to the candidate.")
    identity_transition: bool = switch(
        "Admit the repository identity transition this integration carries."
    )
    release: bool = switch("Release the accepted head.")
    release_head: str = described("", "The release branch head that the release advances.")
    release_base: str = described("", "The base of a maintenance release.")
    tag: str = described("", "The release tag to create.")
    retag: tuple[str, ...] = described((), "Re-create this release tag; repeat for more.")
    original_tag: tuple[str, ...] = described(
        (), "The object a re-created tag named before, as `tag=object`; repeat for more."
    )
    expect_plan_digest: str = described("", "The digest of the previewed re-tag plan.")
    independent_verification_receipt: Path | None = described(
        None, "The receipt of the independent verification that closeout requires."
    )
    acceptance_purpose: AcceptancePurpose = described(
        "repository", "What the landed proof accepts: `repository` or `local-source`."
    )
    change: str | None = described(None, "Integrate this active OpenSpec Change.")


_LAND = "expect_head candidate_head identity_transition acceptance_purpose change"
_CLOSEOUT = "expect_head candidate_head independent_verification_receipt identity_transition change"
_RELEASE = "expect_head release_head release_base tag identity_transition change"
_APPLIED = "read local-evidence-write local-write"

COMMAND = Command(
    name="land",
    summary="Preview or apply candidate, accepted or release integration under current policy.",
    request=LandRequest,
    operations=(
        operation(
            "land.preview",
            "Report whether the lane head can land on the candidate branch.",
            select="apply=false closeout=false release=false retag=unset",
            request=_LAND,
            effects="read",
        ),
        operation(
            "land.apply",
            "Land the lane head on the candidate branch.",
            select="apply=true closeout=false release=false retag=unset",
            request=f"authorize {_LAND}",
            effects=_APPLIED,
            authorization="authorize",
            exit_kind="verdict",
        ),
        operation(
            "land.closeout.preview",
            "Report whether the accepted branch can advance to the candidate.",
            select="closeout=true apply=false release=false retag=unset",
            request=_CLOSEOUT,
            effects="read",
        ),
        operation(
            "land.closeout.apply",
            "Advance the accepted branch to the candidate and rebind its worktrees.",
            select="closeout=true apply=true release=false retag=unset",
            request=f"authorize {_CLOSEOUT}",
            effects=_APPLIED,
            authorization="authorize",
            exit_kind="verdict",
        ),
        operation(
            "land.release.preview",
            "Report whether the accepted head can be released.",
            select="release=true apply=false closeout=false retag=unset",
            request=_RELEASE,
            effects="read",
        ),
        operation(
            "land.release.apply",
            "Release the accepted head under a signed tag.",
            select="release=true apply=true closeout=false retag=unset",
            request=f"authorize {_RELEASE}",
            effects=_APPLIED,
            authorization="authorize",
            exit_kind="verdict",
        ),
        operation(
            "land.retag.preview",
            "Stage the mapped re-tags and report their plan digest.",
            select="retag=set apply=false closeout=false release=false",
            request="original_tag change",
            effects="read local-evidence-write",
        ),
        operation(
            "land.retag.apply",
            "Move the release tags exactly as the previewed plan maps them.",
            select="retag=set apply=true closeout=false release=false",
            request="authorize original_tag expect_plan_digest change",
            effects=_APPLIED,
            authorization="authorize",
            destructive=True,
            exit_kind="verdict",
        ),
    ),
)
