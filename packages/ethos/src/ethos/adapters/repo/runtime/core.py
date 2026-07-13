from __future__ import annotations

import tomllib
from pathlib import Path

import ethos


def _source_root_for_module(module_path: Path) -> Path:
    """Resolve the repository source root that supplied this ETHOS runner."""
    for parent in (module_path.parent, *module_path.parents):
        if (parent / "pyproject.toml").exists() and (
            parent / "packages" / "ethos" / "src" / "ethos" / "__init__.py"
        ).exists():
            return parent
    return module_path.parent


def _schema_source_root(audit_root: Path, runner_source_root: Path) -> Path:
    """Best-effort source root for workspace-status contract validation.

    Product checkouts normally validate against their own tracked schemas. Adopters
    without a complete product schema set fall back to the runner's packaged
    contract source. Keep this read-model lightweight and side-effect free; exact
    schema diagnostics remain owned by the schema validator.
    """
    local = audit_root / "system" / "schemas" / "kernel" / "workspace-status.schema.json"
    if local.exists():
        return audit_root
    runner = runner_source_root / "system" / "schemas" / "kernel" / "workspace-status.schema.json"
    if runner.exists():
        return runner_source_root
    return runner_source_root


def _declares_external_ethos_runner(audit_root: Path) -> bool:
    """Return whether the audited adopter declares ETHOS as its command plane."""
    project = audit_root / ".ethos" / "project.toml"
    try:
        payload = tomllib.loads(project.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return False
    command_plane = payload.get("command_plane")
    if not isinstance(command_plane, dict):
        return False
    public = command_plane.get("public")
    return isinstance(public, str) and "ethos" in public.split()


def runtime_binding(root: Path) -> dict[str, object]:
    """Expose runner/schema/audit binding for agent- and human-friendly diagnosis."""
    audit_root = root.resolve()
    runner_module_path = Path(ethos.__file__).resolve()
    runner_source_root = _source_root_for_module(runner_module_path)
    schema_source_root = _schema_source_root(audit_root, runner_source_root).resolve()
    runner_matches_audit_root = runner_source_root == audit_root
    schema_matches_audit_root = schema_source_root == audit_root
    declared_external_runner = not runner_matches_audit_root and _declares_external_ethos_runner(
        audit_root
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
        else "declared external runner is active; use a checkout-bound runner when changing command or schema surfaces"
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
        "runner_source_root": runner_source_root.as_posix(),
        "schema_source_root": schema_source_root.as_posix(),
        "runner_matches_audit_root": runner_matches_audit_root,
        "schema_matches_audit_root": schema_matches_audit_root,
        "advisory_gaps": advisory_gaps,
        "next_action": next_action,
    }
