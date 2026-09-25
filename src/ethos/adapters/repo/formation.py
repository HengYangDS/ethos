"""Compile and publish an explicitly selected greenfield foundation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from importlib import metadata
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.mutation.lane_lifecycle.candidate_projection import bootstrap_candidate
from ethos.adapters.mutation.lane_lifecycle.start import default_worktree_path
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.adoption import adoption_plan
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.runtime.filesystem import is_junction
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.normalization.coercion import string_sequence

_AGENT_ENTRY = """# Agent Entry

Use the installed ETHOS product: run `ethos status --root . --json` and follow
its current result. Read the reported `agent_guidance.path` for version-matched
operation guidance. OpenSpec owns accepted Change intent; this file grants no
mutation authority.
"""


def formation_plan(
    root: Path,
    *,
    purpose: str,
    starter: str,
    author_name: str = "",
    author_email: str = "",
    apply: bool = False,
    authorized: bool = False,
    expect_plan_digest: str | None = None,
) -> dict[str, object]:
    """Use one candidate for preview or an exact admitted creation effect."""
    requested = root.absolute()
    try:
        parent = requested.parent.resolve(strict=True)
        parent_info = parent.stat()
    except (OSError, RuntimeError):
        return _unavailable(requested, "formation_parent_unsafe")
    target = parent / requested.name
    author = author_name.strip() or os.environ.get("GIT_AUTHOR_NAME", "").strip()
    email = author_email.strip() or os.environ.get("GIT_AUTHOR_EMAIL", "").strip()
    committer = os.environ.get("GIT_COMMITTER_NAME", "").strip() or author
    committer_email = os.environ.get("GIT_COMMITTER_EMAIL", "").strip() or email
    gap = (
        "formation_starter_unavailable"
        if starter not in {"foundation", "python-library"}
        else "formation_purpose_missing"
        if not purpose.strip()
        else "formation_target_exists"
        if requested.exists() or requested.is_symlink() or target.exists() or target.is_symlink()
        else "formation_parent_unsafe"
        if not parent.is_dir()
        else "formation_git_identity_missing"
        if not all((author, email, committer, committer_email))
        else ""
    )
    if gap:
        return _unavailable(target, gap)
    guide = files("ethos").joinpath("data/skills/ethos-repository-work/SKILL.md")
    try:
        guidance_digest = hashlib.sha256(guide.read_bytes()).hexdigest()
        with TemporaryDirectory(prefix=".ethos-preview-", dir=parent) as temporary:
            candidate = Path(temporary) / target.name
            candidate.mkdir()
            binding = adoption_plan(candidate, apply=True)
            if binding["verdict"] != "pass" or binding["applied"] is not True:
                result: dict[str, object] = {
                    "verdict": binding["verdict"],
                    "required_gaps": list(string_sequence(binding.get("required_gaps"))),
                    "root": str(target),
                    "planned_files": [],
                }
            else:
                policy = load_branch_role_policy(candidate)
                candidate_path = default_worktree_path(target, policy.candidate_branch)
                if candidate_path.exists() or candidate_path.is_symlink():
                    return _unavailable(target, "formation_candidate_path_exists") | {
                        "candidate_worktree_path": str(candidate_path)
                    }
                (candidate / "README.md").write_text(
                    f"# {target.name}\n\n{purpose.strip()}\n", encoding="utf-8"
                )
                (candidate / "AGENTS.md").write_text(_AGENT_ENTRY, encoding="utf-8")
                outputs, starter_outputs, starter_gap, detail = _compose_starter(
                    candidate, starter, purpose.strip()
                )
                if starter_gap:
                    return _unavailable(target, starter_gap, detail=detail)
                paths = sorted(outputs)
                sources = {
                    "starter": starter,
                    "product_version": metadata.version("ethos"),
                    "guidance_sha256": guidance_digest,
                    "adoption_plan_digest": str(binding["plan_digest"]),
                    **(
                        {
                            "starter_generator": "uv",
                            "starter_generator_version": metadata.version("uv"),
                        }
                        if starter == "python-library"
                        else {}
                    ),
                    "author_name": author,
                    "author_email": email,
                    "committer_name": committer,
                    "committer_email": committer_email,
                    "requested_root": str(requested),
                    "parent_device": str(parent_info.st_dev),
                    "parent_inode": str(parent_info.st_ino),
                }
                digest = hashlib.sha256(
                    json.dumps(
                        {
                            "root": str(target),
                            "candidate_worktree_path": str(candidate_path),
                            "sources": sources,
                            "outputs": outputs,
                            "starter_outputs": starter_outputs,
                        },
                        sort_keys=True,
                    ).encode()
                ).hexdigest()
                report: dict[str, object] = {
                    "verdict": "pass",
                    "state": "planned",
                    "required_gaps": [],
                    "root": str(target),
                    "candidate_worktree_path": str(candidate_path),
                    "planned_files": paths,
                    "write_plan": [
                        {"path": path, "content_sha256": outputs[path]} for path in paths
                    ],
                    "source_inputs": sources,
                    "starter_outputs": starter_outputs,
                    "plan_digest": digest,
                    "applied": False,
                }
                effect_gap = (
                    "authorization_required"
                    if apply and not authorized
                    else "formation_plan_digest_mismatch"
                    if apply and expect_plan_digest != digest
                    else ""
                )
                if effect_gap:
                    result = _refuse(report, effect_gap)
                elif apply:
                    result = _publish(
                        candidate,
                        target,
                        requested.parent,
                        candidate_path,
                        report,
                        outputs,
                        starter_outputs,
                        sources,
                    )
                else:
                    result = report
    except OSError as error:
        return _unavailable(target, "formation_observation_unavailable", detail=str(error))
    else:
        return result


def _compose_starter(
    candidate: Path, starter: str, purpose: str
) -> tuple[dict[str, str], dict[str, str], str, str]:
    """Let the selected native owner generate optional domain content."""
    foundation, gap, detail = _candidate_outputs(candidate)
    if gap or starter == "foundation":
        return foundation, {}, gap, detail
    generator_gap, detail = _run_python_library_generator(candidate, purpose)
    if generator_gap:
        return {}, {}, generator_gap, detail
    outputs, gap, detail = _candidate_outputs(candidate)
    if gap:
        return outputs, {}, gap, detail
    if any(outputs.get(path) != digest for path, digest in foundation.items()):
        return {}, {}, "formation_starter_overwrote_foundation", ""
    if "pyproject.toml" not in outputs or not any(
        path.startswith("src/") and path.endswith("/__init__.py") for path in outputs
    ):
        return {}, {}, "formation_starter_output_incomplete", "Python library files missing"
    generated = {path: digest for path, digest in outputs.items() if path not in foundation}
    return outputs, generated, "", ""


def _run_python_library_generator(candidate: Path, purpose: str) -> tuple[str, str]:
    """Run only the locked native uv initializer with fixed inert flags."""
    command = (
        sys.executable,
        "-B",
        "-I",
        "-m",
        "uv",
        "init",
        "--lib",
        "--name",
        candidate.name,
        "--description",
        purpose,
        "--vcs",
        "none",
        "--no-readme",
        "--no-pin-python",
        "--no-workspace",
        "--author-from",
        "none",
        "--offline",
        "--no-python-downloads",
        "--no-config",
        "--python",
        "3.12",
        ".",
    )
    try:
        result = run_command(
            candidate,
            command,
            timeout=30,
            env={"UV_NO_CACHE": "1"},
            remove_env=("VIRTUAL_ENV",),
            remove_env_prefixes=("UV_",),
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return "formation_starter_generation_failed", str(error)
    if result.returncode:
        return "formation_starter_generation_failed", (
            result.stderr.strip() or "starter_generator_exit_nonzero"
        )
    return "", ""


def _candidate_outputs(candidate: Path) -> tuple[dict[str, str], str, str]:
    """Inventory only exclusive regular files below an unlinked candidate tree."""
    files: list[Path] = []
    pending = [candidate]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                path = Path(entry.path)
                info = entry.stat(follow_symlinks=False)
                if is_junction(path):
                    return {}, "formation_starter_output_unsafe", str(path)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    files.append(path)
                else:
                    return {}, "formation_starter_output_unsafe", str(path)
    outputs = {
        path.relative_to(candidate).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    return dict(sorted(outputs.items())), "", ""


def _publish(
    candidate: Path,
    target: Path,
    requested_parent: Path,
    candidate_path: Path,
    report: dict[str, object],
    outputs: dict[str, str],
    starter_outputs: dict[str, str],
    sources: dict[str, str],
) -> dict[str, object]:
    """Publish one staged Git repository, then activate its installed runtime."""
    head, gap, detail = _prepare_history(candidate, outputs, starter_outputs, sources)
    if gap:
        return _refuse(report, gap, detail=detail)
    try:
        current_parent = requested_parent.resolve(strict=True)
        info = current_parent.stat()
    except (OSError, RuntimeError):
        return _refuse(report, "formation_parent_changed")
    if (
        current_parent != target.parent
        or str(info.st_dev) != sources["parent_device"]
        or str(info.st_ino) != sources["parent_inode"]
    ):
        return _refuse(report, "formation_parent_changed")
    if target.exists() or target.is_symlink():
        return _refuse(report, "formation_target_exists")
    try:
        shutil.copytree(candidate, target, dirs_exist_ok=False)
    except OSError as error:
        return _uncertain(report, target, "formation_copy_observation_required", str(error))
    return _activate(target, candidate_path, report, outputs, head)


def _prepare_history(
    candidate: Path,
    outputs: dict[str, str],
    starter_outputs: dict[str, str],
    sources: dict[str, str],
) -> tuple[str, str, str]:
    """Create one author-attributed initial commit in scratch."""
    identity = {
        "GIT_AUTHOR_NAME": sources["author_name"],
        "GIT_AUTHOR_EMAIL": sources["author_email"],
        "GIT_COMMITTER_NAME": sources["committer_name"],
        "GIT_COMMITTER_EMAIL": sources["committer_email"],
    }
    for args, gap in (
        (("init", "-q", "--template=", "-b", "dev"), "formation_git_init_failed"),
        (("add", "--", *outputs), "formation_git_add_failed"),
        (("commit", "-q", "-m", "chore: initialize project"), "formation_git_commit_failed"),
    ):
        result = run_git(candidate, *args, check=False, env=identity, timeout=30)
        if result.returncode:
            return "", gap, result.stderr.strip()
    head = run_git(candidate, "rev-parse", "HEAD", timeout=10).stdout.strip()
    try:
        effect = NativeEffect(
            predicate="effect:starter-formation",
            operation="starter.form",
            command=("ethos", "adopt", "--create", "--starter", sources["starter"]),
            subject={"head": head, "starter": sources["starter"]},
            before={
                "sources": {
                    key: sources[key]
                    for key in (
                        "starter",
                        "product_version",
                        "starter_generator",
                        "starter_generator_version",
                    )
                    if key in sources
                }
            },
            after={
                "head": head,
                "starter_outputs": starter_outputs,
                "all_outputs": outputs,
            },
        )
        record_attestation_once(
            candidate,
            issue_native_effect(
                candidate,
                effect=effect,
                state="applied",
                commitment_digest=None,
                repository_id=repository_identity(candidate),
            ),
        )
    except (OSError, ValueError) as error:
        return "", "formation_attestation_failed", str(error)
    return head, "", ""


def _activate(
    target: Path,
    candidate_path: Path,
    report: dict[str, object],
    outputs: dict[str, str],
    head: str,
) -> dict[str, object]:
    """Observe copied bytes, then delegate candidate and runtime activation."""
    try:
        current = run_git(target, "rev-parse", "HEAD", check=False, timeout=10).stdout.strip()
        unchanged = all(
            (target / path).is_file()
            and hashlib.sha256((target / path).read_bytes()).hexdigest() == digest
            for path, digest in outputs.items()
        )
        if current != head or not unchanged:
            return _uncertain(report, target, "formation_postimage_mismatch")
        candidate = bootstrap_candidate(
            root=target, path=candidate_path, expect_head=head, apply=True
        )
        if candidate.get("verdict") != "pass" or candidate.get("state") != "bootstrapped":
            return _uncertain(
                report,
                target,
                "formation_candidate_observation_required",
                ", ".join(string_sequence(candidate.get("required_gaps"))),
            )
        runtime = hook_runtime_binding(target)
        if not runtime["current"] or runtime["required_gaps"]:
            return _uncertain(report, target, "formation_runtime_observation_required")
    except (OSError, ProcessExecutionError, RuntimeError, ValueError) as error:
        return _uncertain(report, target, "formation_effect_observation_required", str(error))
    return report | {
        "state": "applied",
        "applied": True,
        "effect": {
            "root": str(target),
            "head": head,
            "candidate_worktree_path": str(candidate_path),
            "runtime_current": True,
        },
    }


def _refuse(report: dict[str, object], gap: str, *, detail: str = "") -> dict[str, object]:
    return report | {
        "verdict": "block",
        "state": "blocked",
        "required_gaps": [gap],
        "detail": detail,
    }


def _uncertain(
    report: dict[str, object], target: Path, gap: str, detail: str = ""
) -> dict[str, object]:
    return report | {
        "verdict": "unknown",
        "state": "unknown",
        "required_gaps": [gap],
        "effect": {"root": str(target), "target_present": target.exists()},
        "detail": detail,
    }


def _unavailable(target: Path, gap: str, *, detail: str = "") -> dict[str, object]:
    return {
        "verdict": "unknown" if gap == "formation_observation_unavailable" else "block",
        "required_gaps": [gap],
        "root": str(target),
        "planned_files": [],
        "detail": detail,
    }
