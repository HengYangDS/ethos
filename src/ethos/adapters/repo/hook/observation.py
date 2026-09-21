"""Observe installed hook currentness, policy enforcement and declaration read failures."""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NotRequired
from typing import TypedDict

import ethos.adapters.repo.runtime.authority as runtime_authority
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.binding import HOOK_NAMES
from ethos.adapters.repo.hook.binding import HookContract
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook.binding import load_hook_contract
from ethos.adapters.repo.runtime.filesystem import runtime_python
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import legacy_runtime_migration_source
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.adapters.repo.trust_anchor.verification import configured_commit_trust_anchor
from ethos.repository.policy.commit import load_commit_policy
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.retirement import GenerationCleanup
    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity


class HookRuntimeBinding(TypedDict):
    """One repository family's exact generated-hook runtime provenance."""

    required: bool
    hooks_path: str
    runtime_manifest_path: str
    runtime_digest: str
    wheel_sha256: str
    product_version: str
    distribution_version: str
    source_commit: str
    source_tree: str
    expected_source_commit: str
    expected_source_tree: str
    invoking_source_root: NotRequired[str]
    current: bool
    state: str
    target_current: bool
    next_action: str
    python: str
    scripts: list[str]
    required_gaps: list[str]
    generation_cleanup: NotRequired[GenerationCleanup]
    legacy_runtime_locator: NotRequired[dict[str, object]]
    linked_worktrees: NotRequired[list[dict[str, str]]]
    state_transition: NotRequired[dict[str, object]]
    contract_observation: NotRequired[dict[str, object]]


class CommitPolicyEnforcement(TypedDict):
    """Current executability of the optional tracked commit policy."""

    state: str
    declared: bool | None
    declaration: dict[str, object]
    commit_message_transport: str
    push_range_enforcement: str
    required_gaps: list[str]
    next_action: str
    signature_trust: NotRequired[dict[str, object]]


def hook_runtime_binding(
    root: Path,
    *,
    expected_build: BuildIdentity | None = None,
    selected_runtime: SelectedRuntime | None = None,
) -> HookRuntimeBinding:
    """Project one binding, reusing a fresh transaction-local runtime observation."""
    repo = root.resolve()
    common = Path(git_common_dir(repo))
    runtime_root = common / "ethos" / "runtime"
    generations = common / "ethos" / "hooks"
    configured = _configured_hooks_path(repo)
    hooks = configured or generations
    valid_generation = (
        configured is not None
        and configured.parent == generations
        and not generations.parent.is_symlink()
        and not generations.is_symlink()
        and not configured.is_symlink()
        and _valid_digest(configured.name)
    )
    expected, expected_build_gap = _expected_build(repo, expected_build)
    expected_build_identity = expected.identity if expected is not None else None
    build_source = expected.source if expected is not None else None
    expected_source_identity = _expected_source(repo, expected_build_identity)
    if selected_runtime is None:
        selected, selection_gap = _selected_runtime(common)
    else:
        try:
            matches = (runtime_root / "CURRENT").read_bytes() == runtime_selection_bytes(
                common, selected_runtime.root
            )
        except (OSError, ValueError):
            matches = False
        selected, selection_gap = (selected_runtime, "") if matches else (None, "runtime_manifest")
    contract, contract_gap, observation = _hook_contract(selected)
    legacy_source = legacy_runtime_migration_source(common) if selected is None else None
    target_applicable = expected_build_identity is not None
    gaps: list[str] = []
    if not valid_generation:
        gaps.append("write_admission_not_armed:core.hooksPath")
    if expected_build_gap:
        gaps.append(f"write_admission_not_armed:{expected_build_gap}")
    if selection_gap:
        gaps.append(f"write_admission_not_armed:{selection_gap}")
    if contract_gap:
        gaps.append(f"write_admission_not_armed:{contract_gap}")
    source_stale = _source_gap(
        expected_source_identity,
        selected=selected,
        legacy_source=legacy_source,
        gaps=gaps,
    )
    if (
        target_applicable
        and selected is not None
        and selected.build != expected_build_identity
        and not source_stale
    ):
        gaps.append("write_admission_not_armed:runtime_build_stale")
    scripts = contract["scripts"] if contract is not None else HOOK_NAMES
    launchers = (
        contract["launchers"]
        if contract is not None
        else {name: hook_launcher(name) for name in HOOK_NAMES}
    )
    gaps.extend(
        gap
        for name in scripts
        if (gap := _launcher_gap(hooks / name, name, expected=launchers[name]))
    )
    if (
        valid_generation
        and target_applicable
        and contract is not None
        and hooks.name != contract["generation_digest"]
    ):
        gaps.append("write_admission_not_armed:hook_generation_digest")
    return {
        "required": (
            load_repository_profile(repo).exists
            or valid_generation
            or runtime_root.exists()
            or runtime_root.is_symlink()
        ),
        "hooks_path": hooks.as_posix(),
        "runtime_manifest_path": selected.manifest.as_posix() if selected else "",
        "runtime_digest": selected.digest if selected else "",
        "wheel_sha256": selected.wheel_sha256 if selected else "",
        "product_version": selected.build.product_version if selected else "",
        "distribution_version": selected.build.distribution_version if selected else "",
        "source_commit": selected.build.source_commit if selected else "",
        "source_tree": selected.build.source_tree if selected else "",
        "expected_source_commit": expected_source_identity[0] if expected_source_identity else "",
        "expected_source_tree": expected_source_identity[1] if expected_source_identity else "",
        **(
            {"invoking_source_root": build_source.as_posix()}
            if expected is not None and expected.invoking and build_source is not None
            else {}
        ),
        "current": not gaps,
        "state": "unknown"
        if observation
        else "current"
        if not gaps and target_applicable
        else "migration_required"
        if not gaps
        else "stale",
        "target_current": not gaps and target_applicable,
        "next_action": (
            shlex.join(
                (
                    selected.python.as_posix(),
                    "-B",
                    "-I",
                    "-m",
                    "ethos.cli",
                    "status",
                    "--root",
                    repo.as_posix(),
                    "--json",
                )
            )
            if observation and selected is not None
            else _repair_action(
                repo,
                selected,
                source_stale=source_stale,
                build_source=build_source,
                declaration_missing=contract_gap == "runtime_hook_contract_missing",
            )
            if gaps
            else ""
        ),
        "python": selected.python.as_posix() if selected else "",
        "scripts": list(scripts),
        "required_gaps": gaps,
        **({"contract_observation": observation} if observation else {}),
    }


def commit_policy_enforcement(
    root: Path,
    runtime: HookRuntimeBinding,
) -> CommitPolicyEnforcement:
    """Project policy declaration and its two irreducible execution transports."""
    repo = root.resolve()
    try:
        policy = load_commit_policy(repo)
    except (OSError, TypeError, UnicodeError, ValueError) as error:
        gap = str(error).strip() or "commit_policy_invalid"
        return {
            "state": "invalid",
            "declared": None,
            "declaration": {},
            "commit_message_transport": "unknown",
            "push_range_enforcement": "unknown",
            "required_gaps": [gap],
            "next_action": f"repair {(repo / '.ethos/workspace.toml').as_posix()} [commit_policy]",
        }
    if policy is None:
        return {
            "state": "not_declared",
            "declared": False,
            "declaration": {},
            "commit_message_transport": "not_required",
            "push_range_enforcement": "not_required",
            "required_gaps": [],
            "next_action": "",
        }
    if not runtime.get("required_gaps") and "commit-msg" not in runtime.get("scripts", []):
        return {
            "state": "pending_acceptance",
            "declared": True,
            "declaration": policy.projection(),
            "commit_message_transport": "pending_acceptance",
            "push_range_enforcement": "pending_acceptance",
            "required_gaps": [],
            "next_action": "",
        }
    runtime_gaps = tuple(map(str, runtime.get("required_gaps", [])))
    message_gaps = _transport_gaps(runtime_gaps, "commit-msg")
    push_gaps = _transport_gaps(runtime_gaps, "pre-push")
    anchor, trust_gaps = (
        configured_commit_trust_anchor(repo) if policy.signing_required else (None, [])
    )
    gaps = list(dict.fromkeys((*message_gaps, *push_gaps, *trust_gaps)))
    return {
        "state": "unarmed" if message_gaps or push_gaps else "unready" if trust_gaps else "armed",
        "declared": True,
        "declaration": policy.projection(),
        "commit_message_transport": "unarmed" if message_gaps else "armed",
        "push_range_enforcement": "unarmed" if push_gaps else "armed",
        "required_gaps": gaps,
        "signature_trust": {
            "state": "not_required"
            if not policy.signing_required
            else "unready"
            if trust_gaps
            else "configured",
            "anchor": str(anchor or ""),
            "required_gaps": trust_gaps,
        },
        "next_action": (
            str(runtime.get("next_action") or "")
            if message_gaps or push_gaps
            else (
                f"git -C {shlex.quote(str(repo))} config --local "
                "gpg.ssh.allowedSignersFile <absolute-protected-anchor>"
            )
            if trust_gaps
            else ""
        ),
    }


def _transport_gaps(gaps: tuple[str, ...], transport: str) -> tuple[str, ...]:
    launcher_markers = tuple(f":{name}_launcher_" for name in HOOK_NAMES)
    marker = f":{transport}_launcher_"
    return tuple(
        gap for gap in gaps if marker in gap or not any(item in gap for item in launcher_markers)
    )


def _launcher_gap(
    launcher: Path,
    name: str,
    *,
    expected: str | None = None,
) -> str:
    if launcher.is_symlink() or not launcher.is_file() or not os.access(launcher, os.X_OK):
        return f"write_admission_not_armed:{name}_launcher_missing"
    try:
        current = launcher.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        current = ""
    valid = current == (expected if expected is not None else hook_launcher(name))
    return "" if valid else f"write_admission_not_armed:{name}_launcher_drift"


def _hook_contract(
    selected: SelectedRuntime | None,
) -> tuple[HookContract | None, str, dict[str, object]]:
    """Read a declaration owned by the selected immutable runtime inventory."""
    if selected is None:
        return load_hook_contract(), "", {}
    version = ".".join(selected.python_version.split(".")[:2])
    site = (
        selected.root
        / "python"
        / (
            "Lib/site-packages"
            if selected.platform == "windows"
            else f"lib/python{version}/site-packages"
        )
    )
    path = site / "ethos/adapters/repo/hook/binding.toml"
    try:
        return load_hook_contract(path), "", {}
    except FileNotFoundError:
        return None, "runtime_hook_contract_missing", {}
    except (OSError, TypeError, ValueError) as error:
        return (
            None,
            "runtime_hook_contract_unavailable",
            {
                "state": "unknown",
                "reason": "runtime_hook_contract_unavailable",
                "path": path.as_posix(),
                "cause": str(error),
                "effect_attempted": False,
            },
        )


def _source_gap(
    expected: tuple[str, str] | None,
    *,
    selected: SelectedRuntime | None,
    legacy_source: tuple[str, str] | None,
    gaps: list[str],
) -> bool:
    observed = (
        (selected.build.source_commit, selected.build.source_tree)
        if selected is not None
        else legacy_source
    )
    stale = expected is not None and observed is not None and observed != expected
    if expected is None:
        gaps.append("write_admission_not_armed:runtime_expected_source_unavailable")
    elif stale:
        gaps.append("write_admission_not_armed:runtime_build_stale")
        migration_gap = "write_admission_not_armed:runtime_schema_migration_required"
        if migration_gap in gaps:
            gaps.remove(migration_gap)
    return stale


def _selected_runtime(common: Path) -> tuple[SelectedRuntime | None, str]:
    try:
        return current_runtime(common), ""
    except ValueError as error:
        reason = str(error)
        if reason in {"hook_runtime_current_missing", "hook_runtime_current_invalid"}:
            return None, "runtime_current"
        if reason == "hook_runtime_manifest_invalid":
            return None, "runtime_schema_migration_required"
        return None, "runtime_manifest"


def _repair_action(
    repo: Path,
    selected: SelectedRuntime | None,
    *,
    source_stale: bool = False,
    build_source: Path | None = None,
    declaration_missing: bool = False,
) -> str:
    if declaration_missing:
        return shlex.join(
            (
                Path(sys.executable).absolute().as_posix(),
                "-B",
                "-I",
                "-m",
                "ethos.cli",
                "hook",
                "install",
                "--root",
                repo.as_posix(),
                "--json",
            )
        )
    if source_stale and build_source is not None:
        source = build_source.resolve()
        python = runtime_python(source / ".venv")
        return shlex.join(
            (
                python.as_posix(),
                "-B",
                "-I",
                "-m",
                "ethos.cli",
                "hook",
                "install",
                "--root",
                repo.as_posix(),
                "--json",
            )
        )
    if selected is not None and not source_stale:
        return runtime_command(repo, "hook", "install", "--root", repo.as_posix(), "--json")
    return shlex.join(
        (
            Path(sys.executable).resolve().as_posix(),
            "-I",
            "-m",
            "ethos.cli",
            "hook",
            "install",
            "--root",
            repo.as_posix(),
            "--json",
        )
    )


def _expected_build(
    repo: Path,
    selected: BuildIdentity | None,
) -> tuple[runtime_authority.RuntimeBuild | None, str]:
    if selected is not None:
        return runtime_authority.RuntimeBuild(selected, None), ""
    try:
        expected = runtime_authority.expected_runtime_build(repo)
    except GitExecutionError:
        raise
    except (OSError, RuntimeError, ValueError):
        if runtime_authority.accepted_version_migration_pending(repo):
            return None, ""
        return None, "runtime_expected_build_unavailable"
    else:
        return expected, ""


def _expected_source(repo: Path, selected: BuildIdentity | None) -> tuple[str, str] | None:
    if selected is not None:
        return selected.source_commit, selected.source_tree
    try:
        return runtime_authority.expected_runtime_source(repo)
    except GitExecutionError:
        raise
    except (OSError, RuntimeError, ValueError):
        return None


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and not set(value) - set("0123456789abcdef")


def _configured_hooks_path(root: Path) -> Path | None:
    completed = run_git(root, "config", "--path", "--get", "core.hooksPath", check=False)
    if completed.returncode or not completed.stdout.strip():
        return None
    configured = Path(completed.stdout.strip())
    return configured.absolute() if configured.is_absolute() else (root / configured).absolute()
