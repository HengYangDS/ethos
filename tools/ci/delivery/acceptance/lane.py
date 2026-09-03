"""Package-only Work Lane lifecycle acceptance."""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.projection import observe_lease
from ethos.adapters.store.state.schema import state_database
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def prove_lifecycle(
    python: Path,
    repo: Path,
    *,
    environment: Mapping[str, str],
) -> dict[str, dict[str, object]]:
    """Start and recover one Work Lane solely through the installed command plane."""
    prefix = (python.as_posix(), "-B", "-I", "-m", "ethos.cli")
    holder = "agent:test:package-only:bootstrap"
    lane_environment = {**environment, "ETHOS_ACTOR": holder}
    worktree = repo.parent / "repo-work-bootstrap-change"
    command = (
        *prefix,
        "lane",
        "start",
        "bootstrap-change",
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--holder-ref",
        holder,
        "--apply",
        "--json",
    )
    returncode, started, diagnostic = invoke(repo, command, environment=lane_environment)
    if returncode or started.get("verdict") != "pass":
        message = f"package_lane_bootstrap_failed:{diagnostic}"
        raise RuntimeError(message)
    data = started.get("data")
    if not isinstance(data, dict):
        message = "package_lane_bootstrap_result_missing"
        raise TypeError(message)
    bootstrap = data.get("runner_bootstrap")
    expected_command = " ".join(prefix)
    if (
        not isinstance(bootstrap, dict)
        or bootstrap.get("command") != expected_command
        or bootstrap.get("environment_scope") != "git_common_package_runtime"
        or "uv run" in str(bootstrap.get("next_action") or "")
    ):
        message = "package_lane_bootstrap_runtime_invalid"
        raise RuntimeError(message)
    status_args = tuple(shlex.split(str(bootstrap["next_action"])))
    status_code, status, status_diagnostic = invoke(
        worktree,
        status_args,
        environment=lane_environment,
    )
    if status_code or status.get("command") != "status":
        message = f"package_lane_bootstrap_status_failed:{status_diagnostic}"
        raise RuntimeError(message)
    change_root = "openspec/changes/bootstrap-change"
    prewrite = (
        *prefix,
        "lane",
        "prewrite",
        change_root,
        "--editor-root",
        worktree.as_posix(),
        "--require-editor-root",
        "--root",
        worktree.as_posix(),
        "--json",
    )
    _code, prewrite_result, _stderr = invoke(
        worktree,
        prewrite,
        environment=lane_environment,
    )
    if prewrite_result.get("required_gaps") != [
        "openspec_change_metadata_prewrite_required:bootstrap-change"
    ]:
        message = "package_lane_bootstrap_prewrite_invalid"
        raise RuntimeError(message)
    next_action = tuple(shlex.split(str(prewrite_result.get("next_action") or "")))
    if next_action[3:5] != ("--paths", f"{change_root}/.openspec.yaml"):
        message = "package_lane_bootstrap_continuation_invalid"
        raise RuntimeError(message)
    branch = str(data["branch"])
    return {
        "lane_bootstrap": {
            "state": "passed",
            "branch": branch,
            "runtime_command": expected_command,
            "prewrite_gap": prewrite_result["required_gaps"][0],
        },
        "retirement_recovery": _prove_retirement_recovery(
            python,
            repo,
            lane=worktree,
            branch=branch,
            actor=holder,
            environment=environment,
        ),
    }


def _prove_retirement_recovery(
    python: Path,
    repo: Path,
    *,
    lane: Path,
    branch: str,
    actor: str,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Recover one public receipt after its worktree effect completed separately."""
    prefix = (python.as_posix(), "-B", "-I", "-m", "ethos.cli", "lane", "retire")
    lane_environment = {**environment, "ETHOS_ACTOR": actor}
    derive = (
        *prefix,
        "abandon",
        "--branch",
        branch,
        "--reason-code",
        "package-smoke",
        "--reason",
        "exercise installed retirement",
        "--root",
        repo.as_posix(),
        "--json",
    )
    code, derived, diagnostic = invoke(repo, derive, environment=lane_environment)
    if code or derived.get("verdict") != "pass":
        message = f"package_retirement_derivation_failed:{diagnostic}"
        raise RuntimeError(message)
    data = derived.get("data")
    receipt = data.get("receipt") if isinstance(data, dict) else None
    if not isinstance(receipt, dict):
        message = "package_retirement_receipt_missing"
        raise TypeError(message)
    removed = run_git(repo, "worktree", "remove", lane.as_posix(), check=False)
    if removed.returncode:
        message = f"package_retirement_partial_effect_failed:{removed.stderr.strip()}"
        raise RuntimeError(message)
    recover = (
        *prefix,
        "recover",
        "--receipt",
        str(receipt["path"]),
        "--receipt-sha256",
        str(receipt["sha256"]),
        "--root",
        repo.as_posix(),
        "--json",
    )
    _partial_code, partial, _partial_stderr = invoke(
        repo,
        recover,
        environment=lane_environment,
    )
    partial_data = partial.get("data")
    if (
        partial.get("state") != "partial_transition"
        or not isinstance(partial_data, dict)
        or partial_data.get("completed_effects") != ["remove_worktree"]
        or partial_data.get("remaining_effects") != ["delete_ref", "revoke_lease"]
    ):
        message = "package_retirement_partial_state_invalid"
        raise RuntimeError(message)
    apply = (*recover[:-3], "--authorize", "--apply", *recover[-3:])
    applied_code, applied, applied_diagnostic = invoke(
        repo,
        apply,
        environment=lane_environment,
    )
    applied_data = applied.get("data")
    if (
        applied_code
        or applied.get("state") != "retired"
        or not isinstance(applied_data, dict)
        or applied_data.get("remaining_effects") != []
    ):
        message = f"package_retirement_recovery_failed:{applied_diagnostic}"
        raise RuntimeError(message)
    repeated_code, repeated, repeated_diagnostic = invoke(
        repo,
        apply,
        environment=lane_environment,
    )
    if repeated_code or repeated.get("state") != "retired":
        message = f"package_retirement_recovery_not_idempotent:{repeated_diagnostic}"
        raise RuntimeError(message)
    ref = run_git(repo, "branch", "--list", branch, check=False)
    lease_state = observe_lease(state_database(repo), branch).state
    if ref.returncode or ref.stdout.strip() or lease_state != "missing":
        message = "package_retirement_terminal_state_invalid"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "completed_effects": ["remove_worktree", "delete_ref", "revoke_lease"],
        "receipt_sha256": receipt["sha256"],
    }
