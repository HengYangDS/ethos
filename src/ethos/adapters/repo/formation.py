"""Compile and publish an explicitly selected greenfield foundation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from importlib import metadata
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.adoption import adoption_plan
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.activation import install_hook_launchers
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
    target = root.absolute()
    parent = target.parent
    author = author_name.strip() or os.environ.get("GIT_AUTHOR_NAME", "").strip()
    email = author_email.strip() or os.environ.get("GIT_AUTHOR_EMAIL", "").strip()
    committer = os.environ.get("GIT_COMMITTER_NAME", "").strip() or author
    committer_email = os.environ.get("GIT_COMMITTER_EMAIL", "").strip() or email
    gap = (
        "formation_starter_unavailable"
        if starter != "foundation"
        else "formation_purpose_missing"
        if not purpose.strip()
        else "formation_target_exists"
        if target.exists() or target.is_symlink()
        else "formation_parent_unsafe"
        if not parent.is_dir() or _unsafe_path(parent)
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
                return {
                    "verdict": binding["verdict"],
                    "required_gaps": list(string_sequence(binding.get("required_gaps"))),
                    "root": str(target),
                    "planned_files": [],
                }
            (candidate / "README.md").write_text(
                f"# {target.name}\n\n{purpose.strip()}\n", encoding="utf-8"
            )
            (candidate / "AGENTS.md").write_text(_AGENT_ENTRY, encoding="utf-8")
            paths = sorted(
                path.relative_to(candidate).as_posix()
                for path in candidate.rglob("*")
                if path.is_file()
            )
            outputs = {
                path: hashlib.sha256((candidate / path).read_bytes()).hexdigest() for path in paths
            }
            sources = {
                "starter": starter,
                "product_version": metadata.version("ethos"),
                "guidance_sha256": guidance_digest,
                "adoption_plan_digest": str(binding["plan_digest"]),
                "author_name": author,
                "author_email": email,
                "committer_name": committer,
                "committer_email": committer_email,
            }
            digest = hashlib.sha256(
                json.dumps(
                    {"root": str(target), "sources": sources, "outputs": outputs},
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            report: dict[str, object] = {
                "verdict": "pass",
                "state": "planned",
                "required_gaps": [],
                "root": str(target),
                "planned_files": paths,
                "write_plan": [{"path": path, "content_sha256": outputs[path]} for path in paths],
                "source_inputs": sources,
                "plan_digest": digest,
                "applied": False,
            }
            if not apply:
                return report
            effect_gap = (
                "authorization_required"
                if not authorized
                else "formation_plan_digest_mismatch"
                if expect_plan_digest != digest
                else ""
            )
            if effect_gap:
                return _refuse(report, effect_gap)
            return _publish(candidate, target, report, outputs, sources)
    except OSError as error:
        return _unavailable(target, "formation_observation_unavailable", detail=str(error))


def _publish(
    candidate: Path,
    target: Path,
    report: dict[str, object],
    outputs: dict[str, str],
    sources: dict[str, str],
) -> dict[str, object]:
    """Publish one staged Git repository, then activate its installed runtime."""
    head, gap, detail = _prepare_history(candidate, outputs, sources)
    if gap:
        return _refuse(report, gap, detail=detail)
    if target.exists() or target.is_symlink():
        return _refuse(report, "formation_target_exists")
    try:
        shutil.copytree(candidate, target, dirs_exist_ok=False)
    except OSError as error:
        return _uncertain(report, target, "formation_copy_observation_required", str(error))
    return _activate(target, report, outputs, head)


def _prepare_history(
    candidate: Path, outputs: dict[str, str], sources: dict[str, str]
) -> tuple[str, str, str]:
    """Create one author-attributed initial commit and its candidate ref in scratch."""
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
        (("branch", "candidate/dev", "HEAD"), "formation_candidate_ref_failed"),
    ):
        result = run_git(candidate, *args, check=False, env=identity, timeout=30)
        if result.returncode:
            return "", gap, result.stderr.strip()
    head = run_git(candidate, "rev-parse", "HEAD", timeout=10).stdout.strip()
    return head, "", ""


def _activate(
    target: Path, report: dict[str, object], outputs: dict[str, str], head: str
) -> dict[str, object]:
    """Observe copied bytes and refs before activating the selected runtime."""
    try:
        current = run_git(target, "rev-parse", "HEAD", check=False, timeout=10).stdout.strip()
        peer = run_git(target, "rev-parse", "candidate/dev", check=False, timeout=10).stdout.strip()
        unchanged = all(
            (target / path).is_file()
            and hashlib.sha256((target / path).read_bytes()).hexdigest() == digest
            for path, digest in outputs.items()
        )
        if current != head or peer != head or not unchanged:
            return _uncertain(report, target, "formation_postimage_mismatch")
        runtime = install_hook_launchers(target)
        if runtime.get("current") is not True or runtime.get("required_gaps"):
            return _uncertain(report, target, "formation_runtime_observation_required")
    except (OSError, ProcessExecutionError, RuntimeError, ValueError) as error:
        return _uncertain(report, target, "formation_effect_observation_required", str(error))
    return report | {
        "state": "applied",
        "applied": True,
        "effect": {"root": str(target), "head": head, "runtime_current": True},
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


def _unsafe_path(parent: Path) -> bool:
    """Reject a linked or non-directory ancestor before creating scratch state."""
    for component in (parent, *parent.parents):
        try:
            mode = component.lstat().st_mode
        except OSError:
            return True
        if not stat.S_ISDIR(mode):
            return True
    return False


def _unavailable(target: Path, gap: str, *, detail: str = "") -> dict[str, object]:
    return {
        "verdict": "unknown" if gap == "formation_observation_unavailable" else "block",
        "required_gaps": [gap],
        "root": str(target),
        "planned_files": [],
        "detail": detail,
    }
