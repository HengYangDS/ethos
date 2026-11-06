"""Name the build that produced a result, for every surface that returns one.

The CLI and the MCP server share it, and `ethos --version` renders a result without Cyclopts, so
this module imports only the result model and the build identity owner.
"""

from __future__ import annotations

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.runtime.authority import committed_build_identity
from ethos.result import EthosResult


def with_runtime(result: EthosResult) -> EthosResult:
    """Name the build that produced a result, so an agent knows which runtime answered.

    The identity is read once per invocation; when it cannot be read, the result says why and
    still renders.
    """
    try:
        identity = committed_build_identity()
    except (ProcessExecutionError, OSError, ValueError) as error:
        runtime: dict[str, str] = {"unavailable": type(error).__name__}
    else:
        runtime = {
            "product_version": identity.product_version,
            "distribution_version": identity.distribution_version,
            "source_commit": identity.source_commit,
        }
    payload = result.model_dump(exclude_computed_fields=True)
    return EthosResult.model_validate(payload | {"summary": {**result.summary, "runtime": runtime}})
