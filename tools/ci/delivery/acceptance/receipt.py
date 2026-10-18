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
        "repository_activation",
        "signature_repair",
        "native_merge",
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
    command_plane: Mapping[str, object],
    formation: Mapping[str, object],
    brownfield: Mapping[str, object],
    resources: list[str],
    runtime_lifecycle: Mapping[str, Mapping[str, object]],
    generated_at: datetime,
) -> dict[str, object]:
    """Render evidence only after every package lifecycle stage passed."""
    stages = set(runtime_lifecycle)
    passed = all(stage.get("state") == "passed" for stage in runtime_lifecycle.values())
    required = REQUIRED_LIFECYCLE_STAGES
    if stages not in (required, required | {"retained_state_upgrade"}) or not passed:
        message = "package_runtime_lifecycle_incomplete"
        raise ValueError(message)
    if command_plane.get("state") != "passed":
        message = "package_command_plane_incomplete"
        raise ValueError(message)
    if formation.get("state") != "passed":
        message = "package_formation_incomplete"
        raise ValueError(message)
    if formation.get("first_change") != "lane_admitted":
        message = "package_first_change_claim_invalid"
        raise ValueError(message)
    if formation.get("agent_handoff") != "passed":
        message = "package_agent_handoff_incomplete"
        raise ValueError(message)
    if formation.get("formatting") != "passed":
        message = "package_source_format_incomplete"
        raise ValueError(message)
    if (
        brownfield.get("state") != "passed"
        or brownfield.get("authored_content_preserved") is not True
    ):
        message = "package_brownfield_preservation_incomplete"
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
            "command_plane": dict(command_plane),
            "formation": dict(formation),
            "brownfield": dict(brownfield),
            "subprocess_json": True,
            "host_product_independence": dict(independent_host),
            "python_sdk": True,
            "openspec": True,
        },
        "dependencies": "locked_project_environment_projection",
        "module_origins": {"ethos": origin},
        "runtime_lifecycle": dict(runtime_lifecycle),
        "qualification": {
            "fresh_installation": "passed",
            "cross_repository_activation": "passed",
            "retained_state_upgrade": (
                "passed" if "retained_state_upgrade" in stages else "not_qualified"
            ),
            "interruption_recovery": "not_qualified",
            "live_consumer_safe_uninstall": "not_qualified",
        },
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


def package_failure_evidence(
    *,
    head: str,
    wheel_sha256: str,
    error: BaseException,
    owned_work_absent: bool,
    acceptance_written: bool,
    generated_at: datetime,
) -> dict[str, object]:
    """Keep the original failure chain without exposing runtime error messages."""
    error_types: list[str] = []
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        error_types.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    return {
        "schema_version": 1,
        "kind": "ethos_local_install_smoke_terminal",
        "verdict": "block",
        "head": head,
        "wheel_sha256": wheel_sha256,
        "generated_at": generated_at.isoformat(),
        "error_type": type(error).__name__,
        "error_types": error_types,
        "owned_work_absent": owned_work_absent,
        "acceptance_written": acceptance_written,
    }


def runtime_activation_evidence(report: Mapping[str, object]) -> dict[str, object]:
    """Project one successful runtime activation into stable receipt evidence."""
    return {
        "state": "passed",
        "runtime_digest": str(report["runtime_digest"]),
        "wheel_sha256": str(report["wheel_sha256"]),
        "source_commit": str(report["source_commit"]),
        "source_tree": str(report["source_tree"]),
    }
