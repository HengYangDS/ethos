"""Observe execution authority and actual schema provenance for tracked writes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import ethos
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.repository.policy.schema import schema_source_root

if TYPE_CHECKING:
    from ethos.adapters.repo.hook.observation import HookRuntimeBinding
    from ethos.adapters.repo.runtime.selection import SelectedRuntime


def runner_source_root(module_path: Path) -> Path:
    """Resolve the Git checkout that supplied a source runner, when present."""
    try:
        candidate = repository_root(module_path.parent)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError):
        candidate = module_path.parent
    if candidate != module_path.parent:
        try:
            relative = module_path.resolve().relative_to(candidate).as_posix()
        except ValueError:
            relative = ""
        tracked = run_git(candidate, "ls-files", "--error-unmatch", "--", relative, check=False)
        if relative and tracked.returncode == 0:
            return candidate
    return module_path.parent


def runtime_binding(
    root: Path,
    *,
    selected_runtime: SelectedRuntime | None = None,
    hook_binding: HookRuntimeBinding | None = None,
) -> dict[str, object]:
    """Project runner/schema binding, reusing only the caller's current hook observation."""
    audit_root = root.resolve()
    runner_module_path = Path(ethos.__file__).resolve()
    source_root = runner_source_root(runner_module_path)
    schema_root = schema_source_root()
    runner_matches_audit_root = source_root == audit_root
    schema_matches_audit_root = schema_root == audit_root / "system/schemas"
    if hook_binding is None:
        hook_binding = hook_runtime_binding(audit_root, selected_runtime=selected_runtime)
    runner_matches_common_runtime = (
        not hook_binding["required_gaps"]
        and bool(hook_binding["python"])
        and Path(hook_binding["python"]).absolute() == Path(sys.executable).absolute()
    )
    declared_external_runner = False
    if (
        not runner_matches_audit_root
        and not runner_matches_common_runtime
        and not hook_binding["required_gaps"]
        and schema_root == source_root / "system/schemas"
    ):
        if hook_binding.get("invoking_source_root") == source_root.as_posix():
            source = hook_binding["expected_source_commit"], hook_binding["expected_source_tree"]
        else:
            identity = invoking_build_identity()
            source = identity.source_commit, identity.source_tree
        declared_external_runner = source == (
            hook_binding.get("source_commit"),
            hook_binding.get("source_tree"),
        )
    advisory_gaps: list[str] = []
    if not runner_matches_audit_root and not (
        declared_external_runner or runner_matches_common_runtime
    ):
        advisory_gaps.append("workspace_status_runner_source_differs_from_audit_root")
    if not schema_matches_audit_root and not (
        declared_external_runner or runner_matches_common_runtime
    ):
        advisory_gaps.append("workspace_status_schema_source_differs_from_audit_root")
    state = (
        "bound_to_audit_root"
        if runner_matches_audit_root and schema_matches_audit_root
        else "bound_to_common_runtime"
        if runner_matches_common_runtime
        else "external_declared_runner"
        if declared_external_runner
        else "external_current_runner"
    )
    next_action = (
        "runner and its schema source are bound to this repository"
        if state in {"bound_to_audit_root", "bound_to_common_runtime"}
        else (
            "source runner matches the selected runtime build; "
            "use the selected package for installed-product verification"
        )
        if state == "external_declared_runner"
        else (
            "rerun with a package-bound runner from the audited checkout "
            "when changing command or schema surfaces"
        )
    )
    return {
        "kind": "workspace_status_runtime_binding",
        "state": state,
        "audit_root": audit_root.as_posix(),
        "runner_module_path": runner_module_path.as_posix(),
        "runner_source_root": source_root.as_posix(),
        "schema_source_root": schema_root.as_posix(),
        "runner_matches_audit_root": runner_matches_audit_root,
        "schema_matches_audit_root": schema_matches_audit_root,
        "advisory_gaps": advisory_gaps,
        "next_action": next_action,
    }


def runtime_binding_check(status: dict[str, object]) -> dict[str, object]:
    """Reduce one runtime-binding observation to tracked-write admission."""
    binding = status.get("runtime_binding")
    if not isinstance(binding, dict):
        return {"verdict": "unknown", "reason": "runtime_binding_unavailable"}
    audit = str(binding.get("audit_root") or "")
    runner = str(binding.get("runner_source_root") or "")
    schema = str(binding.get("schema_source_root") or "")
    runner_matches = binding.get("runner_matches_audit_root") is True
    schema_matches = binding.get("schema_matches_audit_root") is True
    common_runtime = binding.get("state") == "bound_to_common_runtime"
    selected_source = binding.get("state") == "external_declared_runner"
    matched = bool(audit) and (
        (runner_matches and schema_matches) or common_runtime or selected_source
    )
    return {
        "verdict": "pass" if matched else "block",
        "reason": "matched" if matched else "root_binding_mismatch",
        "audit_root": audit,
        "runner_source_root": runner,
        "schema_source_root": schema,
        "checkout_binding_required": not (common_runtime or selected_source),
        "runner_matches_audit_root": runner_matches,
        "schema_matches_audit_root": schema_matches,
        "runner_matches_common_runtime": common_runtime,
    }
