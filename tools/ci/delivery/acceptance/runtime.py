"""Package-only runtime activation and identity acceptance."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import canonical_architecture
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ethos.repository.release.identity import BuildIdentity


def activate_from_entrypoint(
    executable: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Activate the first immutable runtime from one installed wheel entrypoint."""
    return _activate((executable.as_posix(),), repo, environment=environment)


def activate_from_runtime(
    python: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Activate a successor repository runtime from an immutable package runtime."""
    return _activate(
        (python.as_posix(), "-B", "-I", "-m", "ethos.cli"),
        repo,
        environment=environment,
    )


def _activate(
    prefix: tuple[str, ...],
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, object]:
    command = (*prefix, "hook", "install", "--root", repo.as_posix(), "--json")
    returncode, payload, diagnostic = invoke(repo, command, environment=environment)
    if returncode or payload.get("verdict") != "pass":
        message = f"package_runtime_activation_failed:{diagnostic}"
        raise RuntimeError(message)
    data = payload.get("data")
    if not isinstance(data, dict):
        message = "package_runtime_activation_result_missing"
        raise TypeError(message)
    return data


def require_manifest(
    report: Mapping[str, object],
    repo: Path,
    *,
    build: BuildIdentity,
    wheel_sha256: str,
) -> Path:
    """Require one selected runtime manifest to match its wheel and source identity."""
    try:
        manifest_path = Path(str(report["runtime_manifest_path"]))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        runtime_digest = str(report["runtime_digest"])
        python = Path(str(report["python"]))
    except (KeyError, OSError, json.JSONDecodeError) as error:
        message = "package_runtime_manifest_missing"
        raise RuntimeError(message) from error
    expected_root = Path(git_common_dir(repo)) / "ethos/runtime"
    expected = {
        "schema_version": 6,
        "architecture": canonical_architecture(__import__("platform").machine()),
        "runtime_digest": runtime_digest,
        "wheel_sha256": wheel_sha256,
        **build._asdict(),
    }
    observed = {key: manifest.get(key) for key in expected}
    report_identity = {
        key: report.get(key)
        for key in (
            "product_version",
            "distribution_version",
            "source_commit",
            "source_tree",
            "wheel_sha256",
            "runtime_digest",
        )
    }
    if (
        manifest_path.parent.parent != expected_root
        or manifest_path.parent.name != runtime_digest
        or observed != expected
        or report_identity
        != {
            **build._asdict(),
            "wheel_sha256": wheel_sha256,
            "runtime_digest": runtime_digest,
        }
        or not python.is_file()
    ):
        message = "package_runtime_identity_mismatch"
        raise RuntimeError(message)
    return python


def require_production_dependencies(python: Path) -> dict[str, object]:
    """Require the immutable package runtime to exclude development dependencies."""
    probe = (
        "import importlib.util; "
        "assert importlib.util.find_spec('pytest') is None; "
        "assert importlib.util.find_spec('ruff') is None"
    )
    completed = run_command(
        python.parent,
        (python.as_posix(), "-B", "-I", "-c", probe),
        env={},
        remove_env_prefixes=("GIT_",),
    )
    if completed.returncode:
        message = "package_runtime_development_dependency_present"
        raise RuntimeError(message)
    return {"state": "passed", "excluded": ["pytest", "ruff"]}


def require_version_identity(
    python: Path,
    *,
    build: BuildIdentity,
    wheel_sha256: str,
    runtime_digest: str,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Require the public version surface to expose the complete immutable identity."""
    command = (python.as_posix(), "-B", "-I", "-m", "ethos.cli", "--version", "--json")
    returncode, payload, diagnostic = invoke(python.parent, command, environment=environment)
    data = payload.get("data")
    identity = data.get("identity") if isinstance(data, dict) else {}
    expected = {
        "schema_version": 2,
        **build._asdict(),
        "wheel_sha256": wheel_sha256,
        "runtime_digest": runtime_digest,
    }
    if returncode or identity != expected:
        message = f"package_runtime_version_identity_mismatch:{diagnostic}"
        raise RuntimeError(message)
    return {"state": "passed", "identity": expected}


def prove_repair(
    python: Path,
    repo: Path,
    *,
    hooks_path: Path,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Prove the relocated runtime detects and repairs one stale hook generation."""
    prefix = (python.as_posix(), "-B", "-I", "-m", "ethos.cli")
    status = (*prefix, "status", "--root", repo.as_posix(), "--json")
    returncode, payload, diagnostic = invoke(repo, status, environment=environment)
    data = payload.get("data")
    hook_runtime = data.get("hook_runtime") if isinstance(data, dict) else {}
    if returncode or not isinstance(hook_runtime, dict) or hook_runtime.get("current") is not True:
        message = f"package_runtime_status_failed:{diagnostic}"
        raise RuntimeError(message)
    (hooks_path / "pre-push").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    _returncode, stale, _stderr = invoke(repo, status, environment=environment)
    stale_data = stale.get("data")
    stale_runtime = stale_data.get("hook_runtime") if isinstance(stale_data, dict) else {}
    repair = str(stale_runtime.get("next_action") or "") if isinstance(stale_runtime, dict) else ""
    arguments = tuple(shlex.split(repair))
    if arguments[:5] != prefix or not arguments:
        message = "package_runtime_repair_continuation_invalid"
        raise RuntimeError(message)
    repaired_code, repaired, repaired_diagnostic = invoke(repo, arguments, environment=environment)
    if repaired_code or repaired.get("verdict") != "pass":
        message = f"package_runtime_repair_failed:{repaired_diagnostic}"
        raise RuntimeError(message)
    proof = (*prefix, "prove", "--root", repo.as_posix(), "--json")
    _proof_code, proof_payload, _proof_stderr = invoke(repo, proof, environment=environment)
    if proof_payload.get("command") != "prove":
        message = "package_runtime_proof_surface_invalid"
        raise RuntimeError(message)
    return {"state": "passed", "repair_command": repair}
