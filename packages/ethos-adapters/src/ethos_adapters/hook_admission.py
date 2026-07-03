from __future__ import annotations

from typing import TYPE_CHECKING

from ethos_contracts.branch_roles import PROTECTED_WRITE_ROLES

from ethos_adapters.prewrite import prewrite_guard
from ethos_adapters.status import workspace_status

if TYPE_CHECKING:
    from pathlib import Path

HOOK_LAYERS = {
    "context": {
        "timing": "before_target_resolution",
        "duty": "refresh_repository_truth",
        "fallback": False,
    },
    "pre-tool": {
        "timing": "before_write_capable_tool",
        "duty": "block_unadmitted_tracked_writes",
        "fallback": False,
    },
    "pre-run": {
        "timing": "before_shell_command",
        "duty": "classify_mutation_risk",
        "fallback": False,
    },
    "post-write": {
        "timing": "after_write",
        "duty": "fuse_on_unexpected_mutation",
        "fallback": False,
    },
    "git": {
        "timing": "commit_or_push",
        "duty": "deterministic_local_fallback",
        "fallback": True,
    },
    "ci": {
        "timing": "hosted_pipeline",
        "duty": "integration_and_release_proof",
        "fallback": True,
    },
}

_MUTATION_PATTERNS = (
    " write_text(",
    ".write_text(",
    " >",
    ">>",
    " tee ",
    "sed -i",
    "python -c",
    "rm ",
    "mv ",
    "cp ",
)


def hook_admission_report(
    *,
    root: Path,
    layer: str,
    paths: list[Path] | None = None,
    editor_root: Path | None = None,
    require_editor_root: bool = False,
    command: str = "",
    expected_root: Path | None = None,
) -> dict[str, object]:
    normalized_layer = _normalize_layer(layer)
    repo = root.resolve()
    status = workspace_status(repo)
    target_paths = _target_paths(repo, paths or [])
    base = {
        "ok": True,
        "state": "admitted",
        "layer": normalized_layer,
        "hook": HOOK_LAYERS[normalized_layer],
        "target_root": repo.as_posix(),
        "expected_root": expected_root.resolve().as_posix() if expected_root else repo.as_posix(),
        "role": status["role"],
        "branch": status["branch"],
        "editor_root": editor_root.resolve().as_posix() if editor_root else "",
        "target_paths": [path.as_posix() for path in target_paths],
        "decision": {"action": "allow", "reason": "hook_admitted"},
        "required_gaps": [],
    }
    if normalized_layer == "context":
        return _context_report(base, repo=repo, expected_root=expected_root)
    if normalized_layer == "pre-tool":
        return _prewrite_report(
            base,
            repo=repo,
            paths=target_paths,
            editor_root=editor_root,
            require_editor_root=require_editor_root,
            admitted_reason="prewrite_admitted",
        )
    if normalized_layer == "pre-run":
        return _pre_run_report(
            base,
            repo=repo,
            paths=target_paths,
            editor_root=editor_root,
            require_editor_root=require_editor_root,
            command=command,
        )
    if normalized_layer == "post-write":
        return _post_write_report(base, repo=repo, expected_paths=target_paths)
    return _fallback_report(base)


def _normalize_layer(layer: str) -> str:
    normalized = layer.strip().lower().replace("_", "-")
    if normalized not in HOOK_LAYERS:
        return "pre-tool"
    return normalized


def _target_paths(root: Path, paths: list[Path]) -> list[Path]:
    return [path if path.is_absolute() else root / path for path in paths]


def _context_report(
    base: dict[str, object],
    *,
    repo: Path,
    expected_root: Path | None,
) -> dict[str, object]:
    if expected_root is not None and expected_root.resolve() != repo:
        return _blocked(base, "hook_context_root_mismatch")
    base["state"] = "refreshed"
    base["decision"] = {"action": "allow", "reason": "context_refreshed"}
    return base


def _prewrite_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
    admitted_reason: str,
) -> dict[str, object]:
    admission = prewrite_guard(
        root=repo,
        paths=paths,
        editor_root=editor_root,
        require_editor_root=require_editor_root,
    )
    base["admission"] = admission
    base["role"] = admission["role"]
    base["branch"] = admission["branch"]
    if admission["ok"] is True:
        base["state"] = "admitted"
        base["decision"] = {"action": "allow", "reason": admitted_reason}
        return base
    return _blocked(base, str(admission["error"]))


def _pre_run_report(
    base: dict[str, object],
    *,
    repo: Path,
    paths: list[Path],
    editor_root: Path | None,
    require_editor_root: bool,
    command: str,
) -> dict[str, object]:
    risk = _command_risk(command)
    base["command"] = command
    base["command_risk"] = risk
    if risk["tracked_mutation_risk"] is not True:
        base["state"] = "admitted"
        base["decision"] = {"action": "allow", "reason": "command_observe_only"}
        return base
    if not paths:
        return _blocked(base, "hook_prerun_paths_required")
    return _prewrite_report(
        base,
        repo=repo,
        paths=paths,
        editor_root=editor_root,
        require_editor_root=require_editor_root,
        admitted_reason="prewrite_admitted",
    )


def _command_risk(command: str) -> dict[str, object]:
    lowered = f" {command.lower()} "
    risky = any(pattern in lowered for pattern in _MUTATION_PATTERNS)
    return {
        "tracked_mutation_risk": risky,
        "reason": "command_text_matches_mutation_pattern" if risky else "observe_only_command",
    }


def _post_write_report(
    base: dict[str, object],
    *,
    repo: Path,
    expected_paths: list[Path],
) -> dict[str, object]:
    status = workspace_status(repo)
    changed_paths = [str(path) for path in status["changed_paths"]]
    base["role"] = status["role"]
    base["branch"] = status["branch"]
    base["changed_paths"] = changed_paths
    expected = {_relative(repo, path) for path in expected_paths}
    unexpected = [path for path in changed_paths if not expected or path not in expected]
    base["unexpected_paths"] = unexpected
    if status["role"] in PROTECTED_WRITE_ROLES and changed_paths:
        return _fused(base, "post_write_protected_root_dirty")
    if unexpected:
        return _fused(base, "post_write_unexpected_path")
    base["state"] = "admitted"
    base["decision"] = {"action": "allow", "reason": "post_write_expected_paths_clean"}
    return base


def _relative(root: Path, path: Path) -> str:
    resolved = path if path.is_absolute() else root / path
    try:
        return resolved.resolve().relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _fallback_report(base: dict[str, object]) -> dict[str, object]:
    base["state"] = "fallback"
    base["decision"] = {"action": "allow", "reason": "fallback_hook_layer"}
    base["fallback"] = True
    return base


def _blocked(base: dict[str, object], reason: str) -> dict[str, object]:
    base["ok"] = False
    base["state"] = "blocked"
    base["decision"] = {"action": "block", "reason": reason}
    base["required_gaps"] = [reason]
    return base


def _fused(base: dict[str, object], reason: str) -> dict[str, object]:
    base["ok"] = False
    base["state"] = "fused"
    base["decision"] = {"action": "fuse", "reason": reason}
    base["required_gaps"] = [reason]
    return base
