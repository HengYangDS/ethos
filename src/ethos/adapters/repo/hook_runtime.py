"""Portable Git-hook launchers and the single Python hook execution owner."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import IO
from typing import Literal

from ethos.adapters.admission.git_admission import hook_admission_report
from ethos.adapters.admission.git_admission import push_admission_report
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.git_admission import resolve_ref_move_policy
from ethos.adapters.admission.identity import ReconciliationObservation
from ethos.adapters.admission.prewrite import has_invalid_path_token_character
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.config_effects import set_worktree_config
from ethos.adapters.repo.git import run_command
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.workspace import worktree_records
from ethos.contracts.admission import HookAdmissionRequest
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.verdict import report_verdict
from ethos.repository.hooks import HOOK_NAMES
from ethos.repository.hooks import HookRuntimeBinding
from ethos.repository.hooks import hook_launcher
from ethos.repository.hooks import hook_runtime_binding

HookName = Literal["pre-commit", "pre-push", "reference-transaction"]
_ZERO_OIDS = {"0" * 40, "0" * 64}


def install_hook_launchers(root: Path, *, python: Path | None = None) -> HookRuntimeBinding:
    """Install worktree-local thin launchers bound to one exact Python runtime."""
    repo = root.resolve()
    executable_path = Path(sys.executable) if python is None else python
    if not executable_path.is_absolute() or not executable_path.is_file():
        message = "hook_runtime_python_invalid"
        raise ValueError(message)
    executable = executable_path.as_posix()
    hooks = Path(
        run_git(
            repo,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "ethos-hooks",
        ).stdout.strip()
    )
    metadata = Path(
        run_git(
            repo,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "ethos-runtime-python",
        ).stdout.strip()
    )
    hooks.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(executable + "\n", encoding="utf-8", newline="\n")
    for name in HOOK_NAMES:
        target = hooks / name
        target.write_text(hook_launcher(executable, name), encoding="utf-8", newline="\n")
        target.chmod(0o755)
    set_worktree_config(
        repo,
        {"core.hooksPath": hooks.as_posix(), "gc.packRefs": "false"},
    )
    return hook_runtime_binding(repo)


def execute_hook(
    root: Path,
    name: HookName,
    args: tuple[str, ...],
    *,
    stdin: IO[str],
) -> int:
    """Execute one Git hook without shell-owned policy or PATH-selected ETHOS code."""
    repo = root.resolve()
    try:
        if name == "pre-commit":
            reports = (_pre_commit(repo),)
        elif name == "pre-push":
            reports = _pre_push(repo, args, stdin)
        else:
            reports = _reference_transaction(repo, args, stdin)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        reports = (_blocked(name, str(error) or error.__class__.__name__),)
    failed = [report for report in reports if report_verdict(report) != "pass"]
    if failed:
        sys.stderr.write(json.dumps(failed[0], sort_keys=True) + "\n")
        return 1
    return 0


def _pre_commit(root: Path) -> dict[str, object]:
    staged = _git_paths(root, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD")
    if not staged:
        return _passed("pre-commit", "no_staged_paths")
    _scan_staged_secrets(root)
    _check_staged_python_format(root, staged)
    paths = tuple(
        (root / path).as_posix()
        if not Path(path).is_absolute() and not has_invalid_path_token_character(path)
        else path
        for path in staged
    )
    return hook_admission_report(
        request=HookAdmissionRequest(
            root=root.as_posix(),
            layer="pre-tool",
            paths=paths,
            editor_root=root.as_posix(),
            expected_root=root.as_posix(),
            require_editor_root=True,
            command="git commit",
        )
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
    )
    if completed.returncode:
        message = "staged_secret_scan_failed"
        raise RuntimeError(message)


def _check_staged_python_format(root: Path, staged: tuple[str, ...]) -> None:
    paths = tuple(
        path for path in staged if path.endswith((".py", ".pyi")) and (root / path).exists()
    )
    executable = Path(sys.executable).with_name("ruff.exe" if os.name == "nt" else "ruff")
    if not paths or not (root / "ruff.toml").is_file() or not executable.is_file():
        return
    completed = run_command(
        root,
        (
            executable.as_posix(),
            "format",
            "--cache-dir",
            str(root / "build/runtime/tool-cache/ruff"),
            "--config",
            "ruff.toml",
            "--check",
            *paths,
        ),
    )
    if completed.returncode:
        message = "pre_commit_python_format_failed"
        raise RuntimeError(message)


def _pre_push(root: Path, args: tuple[str, ...], stdin: IO[str]) -> tuple[dict[str, object], ...]:
    remote = args[0] if args else "origin"
    receipt = os.environ.get("ETHOS_RECONCILIATION_RECEIPT", "")
    observations = (
        ReconciliationObservation(
            receipt_path=receipt,
            origin_head=_remote_head(root, "origin", "refs/heads/dev"),
            origin_main_head=_remote_head(root, "origin", "refs/heads/main"),
            github_head=_remote_head(root, "github", "refs/heads/dev"),
            github_main_head=_remote_head(root, "github", "refs/heads/main"),
        )
        if receipt
        else ReconciliationObservation()
    )
    reports = []
    for line in stdin:
        fields = line.split()
        if len(fields) != 4:
            reports.append(_blocked("pre-push", "push_update_invalid"))
            continue
        _local_ref, local_sha, remote_ref, remote_sha = fields
        if local_sha in _ZERO_OIDS:
            continue
        reports.append(
            push_admission_report(
                root=root,
                target_ref=remote_ref,
                pushed_head=local_sha,
                remote_head=remote_sha,
                remote_name=remote,
                reconciliation=observations,
            )
        )
    return tuple(reports) or (_passed("pre-push", "no_push_updates"),)


def _remote_head(root: Path, remote: str, ref: str) -> str:
    completed = run_git(root, "ls-remote", "--exit-code", remote, ref, check=False)
    return completed.stdout.partition("\t")[0].strip() if completed.returncode == 0 else ""


def _reference_transaction(
    root: Path, args: tuple[str, ...], stdin: IO[str]
) -> tuple[dict[str, object], ...]:
    phase = args[0] if args else ""
    if phase not in {"prepared", "committed", "aborted"}:
        return (_passed("reference-transaction", "phase_not_governed"),)
    reports = []
    for line in stdin:
        fields = line.split()
        if len(fields) != 3:
            reports.append(_blocked("reference-transaction", "ref_update_invalid"))
            continue
        old_value, new_value, ref_name = fields
        if not ref_name.startswith("refs/heads/") or (
            old_value == new_value and old_value not in _ZERO_OIDS
        ):
            continue
        reports.append(_reference_transition_report(root, phase, ref_name, old_value, new_value))
    return tuple(reports) or (_passed("reference-transaction", "no_governed_updates"),)


def _reference_transition_report(
    root: Path, phase: str, ref_name: str, old_value: str, new_value: str
) -> dict[str, object]:
    branch = ref_name.removeprefix("refs/heads/")
    try:
        policy = resolve_ref_move_policy(root, ref_name, old_value, new_value)
    except (TypeError, ValueError):
        return _blocked("reference-transaction", "ref_move_policy_unavailable", branch=branch)
    protected = branch == policy.accepted_branch or (
        branch == policy.release_branch and policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    )
    if phase == "prepared" and protected:
        report = _candidate_report(
            root, policy.candidate_branch, ref_name, old_value, new_value, phase
        )
    elif policy.role_for_branch(branch) == ROLE_WORK_LANE:
        report = work_lane_ref_transition_report(
            root=root,
            phase=phase,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
        )
    else:
        report = ref_move_admission_report(
            root=root,
            ref_name=ref_name,
            old_value=old_value,
            new_value=new_value,
            phase=phase,
        )
    if phase in {"aborted", "committed"}:
        return (
            _passed("reference-transaction", f"{phase}_observed") if phase == "aborted" else report
        )
    if policy.role_for_branch(branch) == ROLE_WORK_LANE or protected:
        return report
    decision = report.get("decision")
    return (
        report
        if isinstance(decision, dict) and decision.get("action") == "block"
        else _passed("reference-transaction", "unprotected_ref")
    )


def _candidate_report(
    root: Path,
    candidate_branch: str,
    ref_name: str,
    old_value: str,
    new_value: str,
    phase: str,
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
        return _blocked("reference-transaction", "candidate_semantic_runner_unavailable")
    python = _candidate_python(candidate)
    if python is None:
        return _blocked("reference-transaction", "candidate_semantic_runner_unavailable")
    completed = run_command(
        candidate,
        (
            python.as_posix(),
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
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _blocked("reference-transaction", "candidate_semantic_runner_invalid")
    data = payload.get("data") if isinstance(payload, dict) else None
    return (
        data
        if isinstance(data, dict)
        else _blocked("reference-transaction", "candidate_semantic_runner_invalid")
    )


def _candidate_python(candidate: Path) -> Path | None:
    metadata = run_git(
        candidate,
        "rev-parse",
        "--path-format=absolute",
        "--git-path",
        "ethos-runtime-python",
        check=False,
    )
    if metadata.returncode == 0:
        binding = Path(metadata.stdout.strip())
        if binding.is_file():
            executable = Path(binding.read_text(encoding="utf-8").strip())
            if executable.is_file():
                return executable
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    fallback = candidate / ".venv" / relative
    return fallback if fallback.is_file() else None


def _git_paths(root: Path, *args: str) -> tuple[str, ...]:
    completed = run_git(root, *args, "-z", text=False)
    return tuple(
        raw.decode("utf-8", errors="surrogateescape")
        for raw in completed.stdout.split(b"\0")
        if raw
    )


def _passed(hook: str, state: str) -> dict[str, object]:
    return {"verdict": "pass", "state": state, "hook": hook, "required_gaps": []}


def _blocked(hook: str, gap: str, *, branch: str = "") -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "hook": hook,
        "branch": branch,
        "decision": {"action": "block", "reason": gap},
        "required_gaps": [gap],
    }
