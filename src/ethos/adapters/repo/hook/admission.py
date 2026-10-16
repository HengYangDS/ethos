"""Fresh native hook admission through the existing repository policy owners."""

from __future__ import annotations

import json
import os
import posixpath
import shutil
import subprocess
import sys
import tomllib
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.protocol import blocked_report
from ethos.adapters.repo.hook.protocol import passed_report
from ethos.adapters.repo.runtime.filesystem import runtime_scripts
from ethos.adapters.repo.runtime.selection import SelectedRuntime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.branch.roles import ROLE_RELEASE_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Mapping


def admit_hook(
    root: Path, name: str, args: tuple[str, ...], *, stdin: IO[str]
) -> tuple[dict[str, object], ...]:
    """Validate selected authority before the requested commit or push admission."""
    selected_runtime = current_runtime(Path(git_common_dir(root)))
    selected_index = os.environ.get("GIT_INDEX_FILE")
    index_env = (
        {"GIT_INDEX_FILE": str((root / selected_index).resolve())} if selected_index else None
    )
    if name == "commit-msg":
        return (_commit_msg(root, args, index_env=index_env),)
    if name == "pre-commit":
        return (_pre_commit(root, selected_runtime=selected_runtime, index_env=index_env),)
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
        and import_module(
            "ethos.adapters.repo.worktree_effects"
        ).restore_rejected_checkout_projection(root, target_head=new_value)
    ):
        report["checkout_compensation"] = {
            "state": "restored",
            "head": run_git(root, "rev-parse", "HEAD", check=False).stdout.strip(),
        }
    return report


def _commit_msg(
    root: Path, args: tuple[str, ...], *, index_env: Mapping[str, str] | None = None
) -> dict[str, object]:
    if len(args) != 1:
        return blocked_report("commit-msg", "commit_message_file_missing")
    return import_module("ethos.adapters.repo.commit.admission").commit_message_report(
        root, Path(args[0]), index_env=index_env
    )


def _pre_commit(
    root: Path,
    *,
    selected_runtime: SelectedRuntime,
    index_env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    staged = _git_paths(
        root, "diff", "--cached", "--name-only", "--diff-filter=ACMRTD", index_env=index_env
    )
    if not staged:
        return passed_report("pre-commit", "no_staged_paths")
    with _native_hook_configuration(root, index_env=index_env) as configuration:
        _scan_staged_secrets(root, configuration=configuration, index_env=index_env)
        _check_staged_python_format(root, staged, configuration=configuration, index_env=index_env)
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
        index_env=index_env,
        selected_runtime=selected_runtime,
    )


def _native_configuration_dependency(path: str, source: bytes, *, owner: str) -> str | None:
    """Resolve one native include within its exact repository-relative policy closure."""
    if owner == "gitleaks-ignore":
        return None
    document = tomllib.loads(source.decode("utf-8"))
    policy = document.get("tool", {}).get("ruff", document) if owner == "ruff" else document
    extension = policy.get("extend")
    dependency = extension.get("path") if isinstance(extension, dict) else extension
    if dependency is None:
        return None
    if not isinstance(dependency, str):
        message = f"pre_commit_native_policy_invalid_dependency:{path}"
        raise TypeError(message)
    base = posixpath.dirname(path) if owner == "ruff" else ""
    relative = posixpath.normpath(posixpath.join(base, dependency))
    if relative.startswith(("/", "../")) or relative == "..":
        message = f"pre_commit_native_policy_outside_root:{path}"
        raise ValueError(message)
    return relative


def _reject_noncanonical_policy(root: Path, *, index_env: Mapping[str, str] | None) -> None:
    """Name native policy left at the root instead of silently skipping its check."""
    tools = import_module("ethos.repository.policy.quality.tool_configuration")
    carriers = {
        tools.NATIVE_TOOL_LOCATIONS[tool] for tool in ("gitleaks", "gitleaks-ignore", "ruff")
    }
    paradigm = import_module("ethos.contracts.paradigm.declaration").load_repository_paradigm()
    names = tuple(
        name for tool in paradigm.tool if tool.carrier in carriers for name in tool.root_names
    )
    retained = run_git(root, "ls-files", "--", *names, timeout=30, env=index_env).stdout.split()
    if retained:
        message = f"pre_commit_native_policy_noncanonical:{retained[0]}"
        raise RuntimeError(message)


@contextmanager
def _native_hook_configuration(
    root: Path, *, index_env: Mapping[str, str] | None
) -> Generator[Path]:
    """Project incumbent native policy and its include closure without working-tree reads."""
    tools = import_module("ethos.repository.policy.quality.tool_configuration")
    observed = run_git(root, "rev-parse", "--verify", "HEAD", check=False, timeout=30)
    head = observed.stdout.strip() if not observed.returncode else ""
    _reject_noncanonical_policy(root, index_env=index_env)
    incumbent = _git_paths(root, "ls-tree", "-r", "--name-only", head) if head else ()
    indexed = _git_paths(root, "ls-files", index_env=index_env)
    policies = {
        tool: tools.native_tool_configuration(indexed, tool)
        or tools.native_tool_configuration(incumbent, tool)
        for tool in ("gitleaks", "ruff", "gitleaks-ignore")
    }
    with TemporaryDirectory(prefix="ethos-hook-config-") as temporary:
        configuration = Path(temporary)
        for tool, name in policies.items():
            if name is None:
                continue
            pending, visited = [name], set()
            while pending:
                path = pending.pop()
                if path in visited:
                    continue
                visited.add(path)
                selected = f"{head}:{path}" if name in incumbent else f":{path}"
                source = run_git(
                    root, "show", selected, check=False, text=False, timeout=30, env=index_env
                )
                if source.returncode:
                    message = f"pre_commit_native_policy_unavailable:{path}"
                    raise RuntimeError(message)
                destination = configuration / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.stdout)
                dependency = _native_configuration_dependency(path, source.stdout, owner=tool)
                if dependency is not None:
                    pending.append(dependency)
        yield configuration
        current = run_git(root, "rev-parse", "--verify", "HEAD", check=False, timeout=30)
        if (current.stdout.strip() if not current.returncode else "") != head:
            message = "pre_commit_native_policy_head_changed"
            raise RuntimeError(message)


def _scan_staged_secrets(
    root: Path, *, configuration: Path, index_env: Mapping[str, str] | None = None
) -> None:
    tools = import_module("ethos.repository.policy.quality.tool_configuration")
    policy = configuration / tools.NATIVE_TOOL_LOCATIONS["gitleaks"]
    if not policy.is_file():
        return
    executable = shutil.which("gitleaks")
    if executable is None:
        message = "staged_secret_gitleaks_missing"
        raise RuntimeError(message)
    git_dir = run_git(root, "rev-parse", "--absolute-git-dir", timeout=30).stdout.strip()
    index_path = run_git(
        root, "rev-parse", "--path-format=absolute", "--git-path", "index", timeout=30
    ).stdout.strip()
    selected_env = {
        "GIT_DIR": git_dir,
        "GIT_WORK_TREE": str(configuration),
        "GIT_INDEX_FILE": index_path,
        **(index_env or {}),
    }
    completed = run_command(
        configuration,
        (
            executable,
            "git",
            "--staged",
            "--config",
            str(policy),
            "--gitleaks-ignore-path",
            str(configuration / tools.NATIVE_TOOL_LOCATIONS["gitleaks-ignore"]),
            "--redact=100",
            "--no-banner",
            configuration.as_posix(),
        ),
        remove_env_prefixes=("GIT_", "GITLEAKS_"),
        env=selected_env,
    )
    if completed.returncode:
        message = "staged_secret_scan_failed"
        raise RuntimeError(message)


def _check_staged_python_format(
    root: Path,
    staged: tuple[str, ...],
    *,
    configuration: Path,
    index_env: Mapping[str, str] | None = None,
) -> None:
    tools = import_module("ethos.repository.policy.quality.tool_configuration")
    paths = tuple(path for path in staged if path.endswith((".py", ".pyi")))
    policy = tools.NATIVE_TOOL_LOCATIONS["ruff"]
    if not paths or not (configuration / policy).is_file():
        return
    indexed = set(
        _git_paths(
            root, "diff", "--cached", "--name-only", "--diff-filter=ACMRT", index_env=index_env
        )
    )
    paths = tuple(path for path in paths if path in indexed)
    if not paths:
        return
    try:
        executable = Path(import_module("ruff").find_ruff_bin())
        expected = runtime_scripts(Path(sys.prefix)) / ("ruff.exe" if os.name == "nt" else "ruff")
        if executable.resolve() != expected.resolve() or not os.access(executable, os.X_OK):
            raise FileNotFoundError
    except (ImportError, OSError) as error:
        message = "pre_commit_python_formatter_unavailable"
        raise RuntimeError(message) from error
    for path in paths:
        source = run_git(
            root, "show", f":{path}", check=False, text=False, timeout=30, env=index_env
        )
        if source.returncode:
            message = f"pre_commit_python_index_unavailable:{path}"
            raise RuntimeError(message)
        try:
            completed = run_command(
                configuration,
                (
                    str(executable),
                    "format",
                    "--no-cache",
                    "--config",
                    policy,
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
    remote = args[0] if args else ""
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
    ref_policy = import_module("ethos.adapters.admission.ref_move_policy")
    repair = ref_policy.signature_repair_ref_report(
        root, ref_name, old_value, new_value, phase="prepared"
    ) or import_module("ethos.adapters.admission.role_rename").role_rename_ref_report(
        root, ref_name, old_value, new_value
    )
    if repair is not None:
        return repair
    branch = ref_name.removeprefix("refs/heads/")
    try:
        policy = ref_policy.resolve_ref_move_policy(root, ref_name, old_value, new_value)
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
        report = import_module(
            "ethos.adapters.admission.transitions"
        ).work_lane_ref_transition_report(
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
    policy = import_module("ethos.adapters.admission.ref_move_policy").resolve_ref_move_policy(
        root, ref_name, old_value, new_value
    )
    records = import_module("ethos.adapters.repo.status.workspace").worktree_records(
        root, current_path=root, policy=policy
    )
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
    binding = import_module("ethos.adapters.repo.hook.observation").hook_runtime_binding(
        candidate, selected_runtime=selected_runtime
    )
    if binding["required_gaps"]:
        return None
    python = Path(binding["python"])
    return python if python.is_file() else None


def _git_paths(
    root: Path, *args: str, index_env: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    completed = run_git(root, *args, "-z", text=False, env=index_env)
    return tuple(
        raw.decode("utf-8", errors="surrogateescape")
        for raw in completed.stdout.split(b"\0")
        if raw
    )
