"""Root publication argument and result projection."""

from dataclasses import asdict
from dataclasses import dataclass
from typing import Annotated

from cyclopts import Parameter

from ethos.domain.publication.operation import publish_repository
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.output import emit
from ethos.surface.cli.root_binding import RootOption
from ethos.surface.cli.root_binding import resolve_root


@dataclass(frozen=True, slots=True)
class _PublishOptions:
    """CLI options for `ethos publish`."""

    apply: bool = False
    authorize: bool = False
    expect_head: Annotated[str | None, Parameter(name="--expect-head")] = None
    probe_remote: Annotated[bool, Parameter(name="--probe-remote")] = False
    target_refs: Annotated[tuple[str, ...], Parameter(name="--ref")] = ()
    receipt: Annotated[str | None, Parameter(name="--receipt")] = None
    receipt_sha256: Annotated[str | None, Parameter(name="--receipt-sha256")] = None
    retire: bool = False


_DEFAULT_PUBLISH_OPTIONS = _PublishOptions()


@app.command
def publish(
    options: Annotated[_PublishOptions, Parameter(name="*")] = _DEFAULT_PUBLISH_OPTIONS,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report readiness or project one exact publication operation."""
    repo = resolve_root(root)
    result = publish_repository(repo, **asdict(options))
    projection = bool(options.target_refs) or options.receipt is not None or options.retire
    emit(
        result,
        json_output=json_output,
        enforce=options.apply or (projection and result.verdict == "block"),
        artifact_root=repo if projection else None,
    )
