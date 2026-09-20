"""Fresh native hook admission through the existing repository policy owners."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import IO

from ruff import find_ruff_bin

from ethos.adapters.admission.ref_move_policy import resolve_ref_move_policy
from ethos.adapters.admission.ref_move_policy import signature_repair_ref_report
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.process import run_command
from ethos.adapters.repo.commit.admission import commit_message_report
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.hook.protocol import blocked_report
from ethos.adapters.repo.hook.protocol import passed_report
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from ethos.adapters.repo.runtime.selection import SelectedRuntime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.status.workspace import worktree_records
from ethos.adapters.repo.worktree_effects import restore_rejected_checkout_projection
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_RELEASE_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import report_verdict


def admit_hook(
    root: Path, name: str, args: tuple[str, ...], *, stdin: IO[str]
) -> tuple[dict[str, object], ...]:
    """Validate selected authority before the requested commit or push admission."""
    selected_runtime = current_runtime(Path(git_common_dir(root)))
    if name == "commit-msg":
        return (_commit_msg(root, args),)
    if name == "pre-commit":
        return (_pre_commit(root, selected_runtime=selected_runtime),)
    return _pre_push(root, args, stdin)


def admit_reference(
    root: Path, ref_name: str, old_value: str, new_value: str, *, selected_runtime: SelectedRuntime
) -> dict[str, object]:
    """Admit one prepared ref and retain exact rejected-checkout compensation."""
    report = _prepared_reference_report(
        root, ref_name, old_value, new_value, selected_runtime=selected_runtime
    )
    if (
        report_verdict(report) != "pass"
        and _protected_checkout(root)
        and restore_rejected_checkout_projection(root, target_head=new_value)
    ):
        report["checkout_compensation"] = {
            "state": "restored",
            "head": run_git(root, "rev-parse", "HEAD", check=False).stdout.strip(),
        }
    return report


def _commit_msg(root: Path, args: tuple[str, ...]) -> dict[str, object]:
    if len(args) != 1:
        return blocked_report("commit-msg", "commit_message_file_missing")
    return commit_message_report(root, Path(args[0]))


def _pre_commit(root: Path, *, selected_runtime: SelectedRuntime) -> dict[str, object]:
    staged = _git_paths(root, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD")
    if not staged:
        return passed_report("pre-commit", "no_staged_paths")
    _scan_staged_secrets(root)
    _check_staged_python_format(root, staged)
    prewrite = import_module("ethos.adapters.admission.prewrite")
    paths = tuple(
        (root / path).as_posix()
        if not Path(path).is_absolute() and not prewrite.has_invalid_path_token_character(path)
        else path
        for path in staged
    )
    return prewrite.prewrite_guard(
        root=root,
        paths=[Path(path) for path in paths],
        editor_root=root,
        require_editor_root=True,
        staged=True,
        selected_runtime=selected_runtime,
    )


def _scan_staged_secrets(root: Path) -> None:
    policy = root / ".gitleaks.toml"
    if not policy.is_file():
        return
    executable = shutil.which("gitleaks")
    if executable is None:
        message = "staged_secret_gitleaks_missing"
        raise RuntimeError(message)
    completed = run_command(
        root,
        (
            executable,
            "git",
            "--staged",
            "--config",
            str(policy),
            "--redact=100",
            "--no-banner",
            root.as_posix(),
        ),
        remove_env_prefixes=("GIT_",),
    )
    if completed.returncode:
        message = "staged_secret_scan_failed"
        raise RuntimeError(message)


def _check_staged_python_format(root: Path, staged: tuple[str, ...]) -> None:
    paths = tuple(path for path in staged if path.endswith((".py", ".pyi")))
    if not paths or not (root / "ruff.toml").is_file():
        return
    indexed = set(_git_paths(root, "diff", "--cached", "--name-only", "--diff-filter=ACMRT"))
    paths = tuple(path for path in paths if path in indexed)
    if not paths:
        return
    try:
        executable = Path(find_ruff_bin())
        expected = runtime_scripts(Path(sys.prefix)) / ("ruff.exe" if os.name == "nt" else "ruff")
        if executable.resolve() != expected.resolve() or not os.access(executable, os.X_OK):
            raise FileNotFoundError
    except (ImportError, OSError) as error:
        message = "pre_commit_python_formatter_unavailable"
        raise RuntimeError(message) from error
    for path in paths:
        source = run_git(root, "show", f":{path}", check=False, text=False, timeout=30)
        if source.returncode:
            message = f"pre_commit_python_index_unavailable:{path}"
            raise RuntimeError(message)
        try:
            completed = run_command(
                root,
                (
                    str(executable),
                    "format",
                    "--no-cache",
                    "--config",
                    "ruff.toml",
                    "--check",
                    "--stdin-filename",
                    path,
                    "-",
                ),
                stdin=source.stdout,
                text=False,
                timeout=120,
                remove_env_prefixes=("GIT_",),
            )
        except subprocess.TimeoutExpired as error:
            message = f"pre_commit_python_format_timeout:{path}"
            raise RuntimeError(message) from error
        if completed.returncode:
            message = f"pre_commit_python_format_failed:{path}"
            raise RuntimeError(message)


def _pre_push(root: Path, args: tuple[str, ...], stdin: IO[str]) -> tuple[dict[str, object], ...]:
    remote = args[0] if args else "origin"
    reports = []
    for line in stdin:
        fields = line.split()
        if len(fields) != 4:
            reports.append(blocked_report("pre-push", "push_update_invalid"))
            continue
        _local_ref, local_sha, remote_ref, remote_sha = fields
        reports.append(
            import_module("ethos.adapters.admission.publication").push_admission_report(
                root=root,
                target_ref=remote_ref,
                pushed_head=local_sha,
                remote_head=remote_sha,
                remote_name=remote,
            )
        )
    return tuple(reports) or (passed_report("pre-push", "no_push_updates"),)


def _protected_checkout(root: Path) -> bool:
    policy = load_branch_role_policy(root)
    branch = run_git(root, "branch", "--show-current", check=False).stdout.strip()
    return policy.role_for_branch(branch) in {
        ROLE_RELEASE_ROOT,
        ROLE_ACCEPTED_ROOT,
        ROLE_CANDIDATE,
    }


def _prepared_reference_report(
    root: Path,
    ref_name: str,
    old_value: str,
    new_value: str,
    *,
    selected_runtime: SelectedRuntime,
) -> dict[str, object]:
    repair = signature_repair_ref_report(root, ref_name, old_value, new_value, phase="prepared")
    if repair is not None:
        return repair
    branch = ref_name.removeprefix("refs/heads/")
    try:
        policy = resolve_ref_move_policy(root, ref_name, old_value, new_value)
    except (TypeError, ValueError):
        return blocked_report("reference-transaction", "ref_move_policy_unavailable", branch=branch)
    protected = branch == policy.accepted_branch or (
        branch == policy.release_branch and policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    )
    if protected:
        report = _candidate_report(
            root,
            policy.candidate_branch,
            ref_name,
            old_value,
            new_value,
            "prepared",
            selected_runtime=selected_runtime,
        )
    elif policy.role_for_branch(branch) == ROLE_WORK_LANE:
        report = work_lane_ref_transition_report(
            root=root,
            phase="prepared",
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
        )
    else:
        report = import_module("ethos.adapters.admission.git_admission").ref_move_admission_report(
            root=root,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
            phase="prepared",
        )
    if policy.role_for_branch(branch) == ROLE_WORK_LANE or protected:
        return report
    decision = report.get("decision")
    return (
        report
        if isinstance(decision, dict) and decision.get("action") == "block"
        else passed_report("reference-transaction", "unprotected_ref")
    )


def _candidate_report(
    root: Path,
    candidate_branch: str,
    ref_name: str,
    old_value: str,
    new_value: str,
    phase: str,
    *,
    selected_runtime: SelectedRuntime,
) -> dict[str, object]:
    policy = resolve_ref_move_policy(root, ref_name, old_value, new_value)
    records = worktree_records(root, current_path=root, policy=policy)
    record = next((item for item in records if item.get("branch") == candidate_branch), {})
    candidate = Path(str(record.get("path") or ""))
    if (
        not candidate.is_dir()
        or record.get("head") != new_value
        or run_git(candidate, "status", "--porcelain", check=False).stdout.strip()
    ):
        return blocked_report("reference-transaction", "candidate_semantic_runner_unavailable")
    python = _candidate_python(candidate, selected_runtime=selected_runtime)
    if python is None:
        return blocked_report("reference-transaction", "candidate_semantic_runner_unavailable")
    completed = run_command(
        candidate,
        (
            python.as_posix(),
            "-B",
            "-I",
            "-m",
            "ethos.cli",
            "hook",
            "ref-transaction",
            ref_name,
            old_value,
            new_value,
            "--phase",
            phase,
            "--root",
            root.as_posix(),
            "--json",
        ),
        remove_env_prefixes=("GIT_",),
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return blocked_report("reference-transaction", "candidate_semantic_runner_invalid")
    data = payload.get("data") if isinstance(payload, dict) else None
    return (
        data
        if isinstance(data, dict)
        else blocked_report("reference-transaction", "candidate_semantic_runner_invalid")
    )


def _candidate_python(
    candidate: Path,
    *,
    selected_runtime: SelectedRuntime,
) -> Path | None:
    binding = hook_runtime_binding(candidate, selected_runtime=selected_runtime)
    if binding["required_gaps"]:
        return None
    python = Path(binding["python"])
    return python if python.is_file() else None


def _git_paths(root: Path, *args: str) -> tuple[str, ...]:
    completed = run_git(root, *args, "-z", text=False)
    return tuple(
        raw.decode("utf-8", errors="surrogateescape")
        for raw in completed.stdout.split(b"\0")
        if raw
    )
