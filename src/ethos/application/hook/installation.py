"""Install the hook runtime, and retire the host installations that nothing still needs.

`hook install` converges one Git-common activation and never names its own request as next;
`hook retire-supply` plans, and on an authorized apply retires, the host installations that were
pinned before their consumers were recorded.
"""

import shlex
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from filelock import Timeout

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.hook.activation import HookActivationError
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.rollback import RollbackRefusalError
from ethos.adapters.repo.runtime.host_store import host_store_root
from ethos.adapters.repo.runtime.materialization.host_retention import absent_consumers
from ethos.adapters.repo.runtime.materialization.host_retention import legacy_supply
from ethos.adapters.repo.runtime.materialization.host_retention import repository_common_dirs
from ethos.adapters.repo.runtime.retirement import operational_reference_paths
from ethos.adapters.store.retention.budget import budget_row
from ethos.adapters.store.retention.budget import tree_bytes
from ethos.adapters.store.state.schema import state_schema_report
from ethos.contracts.operations.hook import InstallRequest
from ethos.contracts.operations.hook import RetireSupplyRequest
from ethos.repository.paradigm.parameters import parameter
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
            reason=request.reason,
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
                runtime["next_action"] = _status(root)
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
            str(runtime.get("next_action") or _install_recovery(root, gaps[0], request))
            if gaps
            else _status(root)
            if cleanup_state == "deferred" or legacy_state == "retained"
            else _pin_action(runtime)
        ),
        data=runtime,
    )


def _pin_action(runtime: Mapping[str, object]) -> str:
    """Name what settles an accepted pin that the installation left unselected, if anything."""
    pinned = runtime.get("runtime_pin")
    return str(pinned.get("next_action") or "") if isinstance(pinned, dict) else ""


def _status(root: Path) -> str:
    """Name the inspection that routes the repository to its own next step."""
    return shlex.join(("ethos", "status", "--root", root.resolve().as_posix(), "--json"))


def _install_recovery(repo: Path, gap: str, request: InstallRequest) -> str:
    """Name what recovers an installation, which is never the request that just ran."""
    location = repo.resolve().as_posix()
    if "hook_runtime_installed_supply_" in gap:
        return (
            "select an existing compatible installed ETHOS runtime, then run "
            "ethos hook install --runtime <runtime-root> "
            f"--root {shlex.quote(location)} --json"
        )
    resets = gap in {"state_schema_migration_requires_reset", "state_reset_authorization_required"}
    if resets and not (request.reset_state and request.authorize):
        reset = ("--root", location, "--reset-state", "--authorize", "--json")
        return shlex.join(("ethos", "hook", "install", *reset))
    # Any other gap, a deferred reclamation among them, is re-observed: status names the repair.
    return _status(repo)


def _host_budget(store: Path | None, request: RetireSupplyRequest) -> dict[str, object]:
    """Return a preview's row of the host store's installations against their declared budget."""
    if store is None or request.apply:
        return {}
    held = tree_bytes(store / "installations")["bytes"]
    return {"budget": budget_row(held, parameter("retention", "host_bytes"))}


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
            report |= _supply_plan(store / "installations", root, request, consumers)
        except (OSError, ValueError, Timeout) as error:
            gaps.append(str(error).strip() or error.__class__.__name__)
    gaps.extend(_failure(report))
    planned, done, held, selection = _supply_words(request)
    counts = {
        key: len(value) if isinstance(value := report.get(key), list) else 0
        for key in (planned, "kept", done)
    }
    decision = not request.apply and not gaps and counts[planned] > 0
    scans = [part for path in roots for part in ("--scan", path.as_posix())]
    approve = (
        *scans,
        *selection,
        *("--expect-plan", str(report.get("plan_digest"))),
        *("--apply", "--authorize", "--root", root.as_posix(), "--json"),
    )
    return EthosResult(
        command="hook retire-supply",
        verdict="block" if gaps else "pass",
        state="blocked" if gaps else done if request.apply else "planned",
        summary={**counts, held: report.get(held, 0), **_host_budget(store, request)},
        required_gaps=tuple(gaps),
        user_decision_required=decision,
        next_action=shlex.join(("ethos", "hook", "retire-supply", *approve))
        if decision
        else _cleanup_step(root, request, released=counts[done]),
        data=report,
    )


def _failure(report: dict[str, object]) -> list[str]:
    """Return what stopped a release in the middle; its report keeps what it released."""
    failed = report.get("failed")
    return [str(failed)] if failed else []


def _cleanup_step(root: Path, request: RetireSupplyRequest, *, released: int) -> str:
    """Name the cleanup that follows a release; nothing follows any other outcome.

    A release frees records alone, and the cleanup that ends `hook install` retires what they
    held. A release refused before it began reports none released; one that failed in the middle
    names what it released, and the cleanup follows those.
    """
    if not (request.release_absent and request.apply and released):
        return ""
    return shlex.join(("ethos", "hook", "install", "--root", root.as_posix(), "--json"))


def _supply_plan(
    store: Path, root: Path, request: RetireSupplyRequest, consumers: tuple[Path, ...]
) -> dict[str, object]:
    """Plan, and on apply carry out, the retirement that the request selects."""
    plan = request.expect_plan or None
    if request.release_absent:
        return absent_consumers(store, consumers=consumers, apply=request.apply, expected_plan=plan)
    return legacy_supply(
        store,
        consumers=consumers,
        in_use=lambda: operational_reference_paths(root),
        grace_seconds=request.grace_days * _DAY_SECONDS,
        apply=request.apply,
        expected_plan=plan,
    )


def _supply_words(request: RetireSupplyRequest) -> tuple[str, str, str, tuple[str, ...]]:
    """Name what a request plans, what its apply does, the bytes it sums and its own flags."""
    if request.release_absent:
        return "absent", "released", "held_bytes", ("--release-absent",)
    return "retirable", "retired", "retirable_bytes", ("--grace-days", str(request.grace_days))
