"""The `ethos adopt` request and the nine adoption operations its selectors choose between."""

from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import described
from ethos.contracts.operations.declaration import operation
from ethos.contracts.operations.declaration import switch


class AdoptRequest(CommandRequest):
    """One adoption request: an existing repository, a new one, its starter or its exit."""

    create: bool = switch("Form a new repository at `--root`.")
    evolve_starter: bool = switch("Propose an evolution of the repository's starter.")
    purpose: str = described("", "The project's purpose.")
    starter: str = described("", "The starter: `foundation` or `python-library`.")
    author_name: str = described("", "The first commit's author name.")
    author_email: str = described("", "The first commit's author email.")
    signing_key: str = described("", "The key that signs the first commit.")
    trust_anchor: str = described("", "The trust anchor that admits the signing key.")
    signing_program: str = described("", "The program that signs the first commit.")
    apply: bool = switch("Apply the selected operation instead of previewing it.")
    authorize: bool = switch("Authorize the apply.")
    expect_head: str | None = described(None, "The repository head the operation expects.")
    expect_plan_digest: str | None = described(None, "The digest of the previewed plan.")
    select_runtime: bool = switch("Also select the repository's immutable runtime.")
    exit_repository: bool = switch("Leave ETHOS: restore what adoption replaced.")


_FORMATION = "purpose starter author_name author_email signing_key trust_anchor signing_program"
_APPLY = "authorize expect_head expect_plan_digest"
_EXISTING = "create=false evolve_starter=false exit_repository=false"

COMMAND = Command(
    name="adopt",
    summary="Plan or apply ETHOS adoption for a repository, or preview and apply its exit.",
    request=AdoptRequest,
    spellings=(("exit_repository", "exit"),),
    operations=(
        operation(
            "adopt.preview",
            "Plan the adoption of this repository.",
            select=f"{_EXISTING} select_runtime=false apply=false",
            request="expect_head",
            effects="read",
        ),
        operation(
            "adopt.apply",
            "Apply the previewed adoption.",
            select=f"{_EXISTING} select_runtime=false apply=true",
            request=_APPLY,
            effects="read local-write",
            authorization="authorize",
            exit_kind="verdict",
        ),
        operation(
            "adopt.runtime.preview",
            "Plan the adoption with the selection of the repository's runtime.",
            select=f"{_EXISTING} select_runtime=true apply=false",
            request="expect_head",
            effects="read",
        ),
        operation(
            "adopt.runtime.apply",
            "Apply the previewed adoption and select the runtime.",
            select=f"{_EXISTING} select_runtime=true apply=true",
            request=_APPLY,
            effects="read local-write host-write",
            authorization="authorize",
            exit_kind="verdict",
        ),
        operation(
            "adopt.create.preview",
            "Plan the formation of a new repository.",
            select="create=true evolve_starter=false exit_repository=false select_runtime=false "
            "apply=false",
            request=_FORMATION,
            effects="read execute",
            creates_root=True,
        ),
        operation(
            "adopt.create.apply",
            "Form the previewed repository.",
            select="create=true evolve_starter=false exit_repository=false select_runtime=false "
            "apply=true",
            request=f"{_FORMATION} authorize expect_plan_digest",
            effects="read execute host-write",
            authorization="authorize",
            exit_kind="verdict",
            creates_root=True,
        ),
        operation(
            "adopt.evolve-starter.preview",
            "Propose a starter evolution; its changes apply through an owned Work Lane.",
            select="evolve_starter=true create=false exit_repository=false select_runtime=false "
            "apply=false",
            request="purpose starter expect_head",
            effects="read execute",
        ),
        operation(
            "adopt.exit.preview",
            "Preview this repository's exit from ETHOS.",
            select="exit_repository=true create=false evolve_starter=false select_runtime=false "
            "apply=false",
            request="expect_head",
            effects="read",
        ),
        operation(
            "adopt.exit.apply",
            "Apply exactly the previewed exit.",
            select="exit_repository=true create=false evolve_starter=false select_runtime=false "
            "apply=true",
            request=_APPLY,
            effects="read local-evidence-write local-write host-write",
            authorization="authorize",
            destructive=True,
            exit_kind="verdict",
        ),
    ),
)
