"""Install the hook runtime, and retire the host installations that nothing still needs.

`hook install` converges one Git-common activation and names the command that recovers it;
`hook retire-supply` plans, and on an authorized apply retires, the host installations that were
pinned before their consumers were recorded.
"""

import shlex
from pathlib import Path
from typing import Any

from filelock import Timeout

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.hook.activation import HookActivationError
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.rollback import RollbackRefusalError
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.adapters.repo.runtime.materialization.host_retention import legacy_supply
from ethos.adapters.repo.runtime.materialization.host_retention import repository_common_dirs
from ethos.adapters.repo.runtime.retirement import operational_reference_paths
from ethos.adapters.store.state.schema import state_schema_report
from ethos.contracts.operations.hook import InstallRequest
from ethos.contracts.operations.hook import RetireSupplyRequest
from ethos.result import EthosResult

_DAY_SECONDS = 24 * 3600


def _uninstalled(next_action: str = "") -> dict[str, Any]:
    """Describe an install that activated nothing, with the action that can proceed."""
    return {
        "hooks_path": "",
        "python": "",
        "scripts": [],
        "linked_worktrees": [],
        "generation_cleanup": {
            "checked": [],
            "removed": [],
            "retained": [],
            "unproven_removals": [],
        },
        **({"next_action": next_action} if next_action else {}),
    }


def install_hook_runtime(root: Path, request: InstallRequest) -> EthosResult:
    """Converge the repository-family hook runtime through Git-common activation."""
    runtime_root = request.installed_runtime
    try:
        runtime = install_hook_launchers(
            root,
            installed_runtime=Path(runtime_root) if runtime_root is not None else None,
            reset_state=request.reset_state,
            authorized=request.authorize,
        )
    except RollbackRefusalError as refusal:
        gaps = (refusal.gap,)
        runtime = _uninstalled(refusal.next_action)
    except (OSError, RuntimeError, ValueError) as error:
        reason = str(error).strip() or error.__class__.__name__
        state_failure = reason.startswith("state_")
        gaps = (reason,) if state_failure else (f"hook_install_failed:{reason}",)
        runtime = _uninstalled()
        if isinstance(error, (ProcessExecutionError, HookActivationError)):
            if isinstance(error, ProcessExecutionError):
                runtime["process_failure"] = error.evidence()
            else:
                runtime["contract_observation"] = error.observation
            if error.observation:
                runtime["next_action"] = shlex.join(
                    ("ethos", "status", "--root", root.as_posix(), "--json")
                )
        if state_failure:
            try:
                runtime["state_schema"] = state_schema_report(root)
            except (OSError, ValueError):
                runtime["state_schema"] = {
                    "expected_state": "current",
                    "observed_state": "unavailable",
                }
    else:
        gaps = tuple(str(gap) for gap in runtime.get("required_gaps", []))
    linked = runtime.get("linked_worktrees", [])
    cleanup = runtime.get("generation_cleanup")
    removed = cleanup.get("removed", []) if isinstance(cleanup, dict) else []
    removed_count = len(removed) if isinstance(removed, list) else 0
    unproven = cleanup.get("unproven_removals", []) if isinstance(cleanup, dict) else []
    unproven_count = len(unproven) if isinstance(unproven, list) else 0
    cleanup_state = str(cleanup.get("state") or "") if isinstance(cleanup, dict) else ""
    legacy = runtime.get("legacy_runtime_locator")
    legacy_state = str(legacy.get("state") or "") if isinstance(legacy, dict) else ""
    state_transition = runtime.get("state_transition")
    activated = runtime.get("current") is True
    return EthosResult(
        command="hook install",
        verdict="block" if gaps else "pass",
        state=(
            "installed_cleanup_deferred"
            if gaps and activated
            else "blocked"
            if gaps
            else "installed"
        ),
        summary={
            "hooks_path": runtime["hooks_path"],
            "python": runtime["python"],
            "wired": activated,
            "pack_refs_disabled": activated,
            "linked_worktrees_checked": len(linked),
            "linked_worktrees_repaired": sum(
                item.get("state") == "repaired" for item in linked if isinstance(item, dict)
            ),
            "generated_paths_removed": removed_count,
            "generation_removals_unproven": unproven_count,
            "generation_cleanup": cleanup_state,
            "legacy_runtime_locator": legacy_state,
            "state_transition": (
                str(state_transition.get("state") or "")
                if isinstance(state_transition, dict)
                else ""
            ),
        },
        required_gaps=gaps,
        user_decision_required=bool(gaps and "hook_runtime_installed_supply_" in gaps[0]),
        next_action=(
            str(runtime.get("next_action") or _install_recovery(root, gaps[0]))
            if gaps
            else _install_recovery(root, "")
            if cleanup_state == "deferred" or legacy_state == "retained"
            else ""
        ),
        data=runtime,
    )


def _install_recovery(repo: Path, gap: str) -> str:
    command = ["ethos", "hook", "install", "--root", repo.resolve().as_posix()]
    if "hook_runtime_installed_supply_" in gap:
        return (
            "select an existing compatible installed ETHOS runtime, then run "
            "ethos hook install --runtime <runtime-root> "
            f"--root {shlex.quote(repo.resolve().as_posix())} --json"
        )
    if gap in {"state_schema_migration_requires_reset", "state_reset_authorization_required"}:
        command.extend(("--reset-state", "--authorize"))
    command.append("--json")
    return shlex.join(command)


def retire_host_supply(root: Path, request: RetireSupplyRequest) -> EthosResult:
    """Preview host installations pinned before consumers were recorded; retire an approved plan."""
    roots = tuple(Path(path).resolve() for path in request.scan)
    store = host_store_root()
    consumers = repository_common_dirs(roots) if roots and all(map(Path.is_dir, roots)) else ()
    gaps: list[str] = []
    if not consumers:
        gaps.append("host_store_scan_root_invalid")
    elif store is None:
        gaps.append("hook_runtime_host_store_invalid")
    elif request.apply and not request.authorize:
        gaps.append("authorization_required")
    elif request.apply and not request.expect_plan:
        gaps.append("host_store_plan_required")
    report: dict[str, object] = {"scanned_repositories": [path.as_posix() for path in consumers]}
    if not gaps and store is not None:
        try:
            report |= legacy_supply(
                store / "installations",
                consumers=consumers,
                in_use=lambda: operational_reference_paths(root),
                grace_seconds=request.grace_days * _DAY_SECONDS,
                apply=request.apply,
                expected_plan=request.expect_plan or None,
            )
        except (OSError, ValueError, Timeout) as error:
            gaps.append(str(error).strip() or error.__class__.__name__)
    counts = {
        key: len(value) if isinstance(value := report.get(key), list) else 0
        for key in ("retirable", "kept", "retired")
    }
    decision = not request.apply and not gaps and counts["retirable"] > 0
    scans = [part for path in roots for part in ("--scan", path.as_posix())]
    approve = (
        *scans,
        *("--grace-days", str(request.grace_days)),
        *("--expect-plan", str(report.get("plan_digest"))),
        *("--apply", "--authorize", "--root", root.as_posix(), "--json"),
    )
    return EthosResult(
        command="hook retire-supply",
        verdict="block" if gaps else "pass",
        state="blocked" if gaps else "retired" if request.apply else "planned",
        summary={**counts, "retirable_bytes": report.get("retirable_bytes", 0)},
        required_gaps=tuple(gaps),
        user_decision_required=decision,
        next_action=shlex.join(("ethos", "hook", "retire-supply", *approve)) if decision else "",
        data=report,
    )
