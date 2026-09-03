"""Pure package-acceptance evidence contract."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from pathlib import Path

REQUIRED_LIFECYCLE_STAGES = frozenset(
    {
        "development_dependencies",
        "hook_activation",
        "immutable_identity",
        "lane_bootstrap",
        "relocation_repair",
        "retirement_recovery",
        "successor_activation",
    }
)


def package_acceptance_evidence(
    *,
    root: Path,
    head: str,
    wheel: Path,
    origin: str,
    version: str,
    line_endings: list[str],
    independent_host: Mapping[str, object],
    resources: list[str],
    runtime_lifecycle: Mapping[str, Mapping[str, object]],
    generated_at: datetime,
) -> dict[str, object]:
    """Render evidence only after every package lifecycle stage passed."""
    stages = set(runtime_lifecycle)
    passed = all(stage.get("state") == "passed" for stage in runtime_lifecycle.values())
    if stages != REQUIRED_LIFECYCLE_STAGES or not passed:
        message = "package_runtime_lifecycle_incomplete"
        raise ValueError(message)
    try:
        wheel_path = wheel.relative_to(root).as_posix()
    except ValueError:
        wheel_path = wheel.name
    return {
        "schema_version": 2,
        "kind": "ethos_local_install_smoke_evidence",
        "verdict": "pass",
        "state": "passed",
        "head": head,
        "command": "uv run --frozen --offline python -m nox -s install_smoke",
        "generated_at": generated_at.isoformat(),
        "head_stability": "verified_before_evidence_write",
        "offline": True,
        "fresh_environment": True,
        "host": {
            "line_endings": line_endings,
        },
        "conformance": {
            "subprocess_json": True,
            "host_product_independence": dict(independent_host),
            "python_sdk": True,
            "openspec": True,
        },
        "dependencies": "locked_project_environment_projection",
        "module_origins": {"ethos": origin},
        "runtime_lifecycle": dict(runtime_lifecycle),
        "wheel_resources": resources,
        "version": version,
        "wheels": [
            {
                "path": wheel_path,
                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
        ],
        "hosted_ci_status_claimed": False,
        "remote_publication_claimed": False,
        "registry_publication_claimed": False,
    }
