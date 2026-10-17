"""Render the shared adoption operation through Cyclopts."""

from ethos.domain.adoption import adopt_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@app.command
def adopt(
    *,
    root: RootOption | None = None,
    create: bool = False,
    evolve_starter: bool = False,
    purpose: str = "",
    starter: str = "",
    author_name: str = "",
    author_email: str = "",
    signing_key: str = "",
    trust_anchor: str = "",
    signing_program: str = "",
    apply: bool = False,
    authorize: bool = False,
    expect_head: str | None = None,
    expect_plan_digest: str | None = None,
    select_runtime: bool = False,
    json_output: JsonFlag = False,
) -> None:
    """Plan or apply ETHOS adoption for a repository."""
    if create and root is None:
        message = "formation_root_required"
        raise ValueError(message)
    target = root if create and root is not None else resolve_root(root)
    result = adopt_repository(
        target,
        create=create,
        evolve_starter=evolve_starter,
        purpose=purpose,
        starter=starter,
        author_name=author_name,
        author_email=author_email,
        signing_key=signing_key,
        trust_anchor=trust_anchor,
        signing_program=signing_program,
        apply=apply,
        authorize=authorize,
        expect_head=expect_head,
        expect_plan_digest=expect_plan_digest,
        select_runtime=select_runtime,
    )
    emit(result, json_output=json_output, enforce=apply)
