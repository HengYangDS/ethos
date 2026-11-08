"""Project a result for the surface that returns it: its build, its payload bound and its identity.

The CLI and the MCP server share this module, and `ethos --version` renders through it without
Cyclopts, so it imports neither the console nor a surface. A bounded result writes its oversized
detail to the store of the repository that its caller anchors it to.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ethos.adapters.openspec.cli import OFFICIAL_VERSION
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.authority import committed_build_identity
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.result import EthosResult
from ethos.result import apply_payload_budget


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


def bounded_result(result: EthosResult, *, anchor: Path | None) -> EthosResult:
    """Name the result's build and bound its payload; detail goes to the anchor's store.

    The store is resolved only when detail is written, so a small result, including the report of
    a failed process, never spawns one. No anchor means the current directory.
    """
    return apply_payload_budget(with_runtime(result), root=lambda: _detail_store(anchor))


def version_result() -> EthosResult:
    """Return the invoking build's identity, with the runtime artifacts that installed it."""
    identity = invoking_build_identity()
    runtime_digest, wheel_sha256 = _runtime_artifacts()
    projection = identity.projection() | {
        "wheel_sha256": wheel_sha256,
        "runtime_digest": runtime_digest,
    }
    return EthosResult(
        command="version",
        verdict="pass",
        state="identified",
        summary={
            "product_version": identity.product_version,
            "distribution_version": identity.distribution_version,
        },
        data={"identity": projection, "openspec_version": OFFICIAL_VERSION},
    )


def _detail_store(anchor: Path | None) -> Path:
    """Return the ETHOS store of the anchored repository, for its detail cache."""
    root = anchor or Path.cwd()
    try:
        common_dir = git_common_dir(root)
    except ProcessExecutionError as error:
        # The bound treats an unresolvable store like an unwritable one: the result stays inline.
        raise OSError(error.code) from error
    return Path(common_dir) / "ethos" if common_dir else root / ".ethos"


def _runtime_artifacts() -> tuple[str, str]:
    runtime = Path(sys.prefix).resolve().parent
    if Path(sys.prefix).name != "python" or runtime.parent.name != "runtime":
        return "", ""
    try:
        selected = require_selected_runtime(runtime, carrier=True)
    except (OSError, ValueError):
        return "", ""
    return selected.digest, selected.wheel_sha256
