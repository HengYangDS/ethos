from __future__ import annotations

import subprocess
from pathlib import Path

import ethos
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.repository.profile import load_repository_profile


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


def _schema_source_root(audit_root: Path, runner_root: Path) -> Path:
    """Best-effort source root for workspace-status contract validation.

    Product checkouts normally validate against their own tracked schemas. Adopters
    without a complete product schema set fall back to the runner's packaged
    contract source. Keep this read-model lightweight and side-effect free; exact
    schema diagnostics remain owned by the schema validator.
    """
    local = audit_root / "system" / "schemas" / "kernel" / "workspace-status.schema.json"
    if local.exists():
        return audit_root
    return runner_root


def runtime_binding(root: Path) -> dict[str, object]:
    """Expose runner/schema/audit binding for agent- and human-friendly diagnosis."""
    audit_root = root.resolve()
    runner_module_path = Path(ethos.__file__).resolve()
    source_root = runner_source_root(runner_module_path)
    schema_source_root = _schema_source_root(audit_root, source_root).resolve()
    runner_matches_audit_root = source_root == audit_root
    schema_matches_audit_root = schema_source_root == audit_root
    declared_external_runner = (
        not runner_matches_audit_root and load_repository_profile(audit_root).state == "valid"
    )
    advisory_gaps: list[str] = []
    if not runner_matches_audit_root and not declared_external_runner:
        advisory_gaps.append("workspace_status_runner_source_differs_from_audit_root")
    if not schema_matches_audit_root and not declared_external_runner:
        advisory_gaps.append("workspace_status_schema_source_differs_from_audit_root")
    state = (
        "bound_to_audit_root"
        if runner_matches_audit_root and schema_matches_audit_root
        else "external_declared_runner"
        if declared_external_runner
        else "external_current_runner"
    )
    next_action = (
        "runner, schema, and audit root are aligned"
        if state == "bound_to_audit_root"
        else (
            "declared external runner is active; use a checkout-bound runner "
            "when changing command or schema surfaces"
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
        "schema_source_root": schema_source_root.as_posix(),
        "runner_matches_audit_root": runner_matches_audit_root,
        "schema_matches_audit_root": schema_matches_audit_root,
        "advisory_gaps": advisory_gaps,
        "next_action": next_action,
    }
