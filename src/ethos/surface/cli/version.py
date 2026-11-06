"""Public human and machine projections of the invoking build identity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ethos.adapters.openspec.cli import OFFICIAL_VERSION
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.result import EthosResult
from ethos.surface.cli.runtime_identity import with_runtime


def version_text() -> str:
    """Render one identity result for Cyclopts' built-in version surface."""
    identity = invoking_build_identity()
    runtime_digest, wheel_sha256 = _runtime_artifacts()
    projection = identity.projection() | {
        "wheel_sha256": wheel_sha256,
        "runtime_digest": runtime_digest,
    }
    if "--json" in sys.argv[1:]:
        result = EthosResult(
            command="version",
            verdict="pass",
            state="identified",
            summary={
                "product_version": identity.product_version,
                "distribution_version": identity.distribution_version,
            },
            data={"identity": projection, "openspec_version": OFFICIAL_VERSION},
        )
        payload = with_runtime(result).to_dict()
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        f"ethos {identity.product_version} "
        f"({identity.distribution_version}; {identity.source_commit[:12]}; "
        f"OpenSpec {OFFICIAL_VERSION})"
    )


def _runtime_artifacts() -> tuple[str, str]:
    runtime = Path(sys.prefix).resolve().parent
    if Path(sys.prefix).name != "python" or runtime.parent.name != "runtime":
        return "", ""
    try:
        selected = require_selected_runtime(runtime, carrier=True)
    except (OSError, ValueError):
        return "", ""
    return selected.digest, selected.wheel_sha256
