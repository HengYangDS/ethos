"""Exercise packaged merge continuation on a native, independently signed fixture."""

from __future__ import annotations

import base64
import json
import os
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.trust_anchor.verification import verify_commit_trust
from tools.ci.delivery.acceptance.invocation import invoke

if TYPE_CHECKING:
    from collections.abc import Mapping


def _git(root: Path, *args: str, environment: Mapping[str, str]) -> str:
    """Run native fixture setup without importing source lifecycle behavior."""
    result = run_command(
        root,
        ("git", *args),
        env={
            **environment,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
        inherit_environment=False,
        timeout=30,
    )
    if result.returncode:
        message = f"package_merge_git_failed:{shlex.join(args)}:{result.stderr.strip()}"
        raise RuntimeError(message)
    return result.stdout.strip()


def _change(root: Path, name: str) -> None:
    """Write complete official intent for one disposable contribution."""
    target = root / "openspec/changes" / name
    target.mkdir(parents=True)
    sources = {
        ".openspec.yaml": "schema: spec-driven\n",
        "proposal.md": "## Why\n\nVerify installed native merge.\n\n"
        "## What Changes\n\n- Merge independent contributions.\n\n"
        "## Out of Scope\n\n- Product changes.\n",
        "design.md": "## Context\n\nDisposable package-only verification.\n",
        "tasks.md": "## 1. Integration\n\n- [ ] 1.1 Verify contribution.\n",
        "specs/merge/spec.md": "## ADDED Requirements\n\n"
        "### Requirement: Contribution identity\n\n"
        "The merge SHALL preserve both contribution parents.\n\n"
        "#### Scenario: Independent contributions\n\n"
        "- **WHEN** contributions are integrated\n- **THEN** both parents remain\n",
    }
    for relative, content in sources.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _prepare_fixture(repo: Path, env: Mapping[str, str]) -> tuple[Path, Path, str, str]:
    """Establish exact independent parent histories before installing governance."""
    target = repo.parent / "merge-adopter"
    _git(repo, "clone", "--no-hardlinks", "--no-local", str(repo), str(target), environment=env)
    _git(target, "remote", "remove", "origin", environment=env)
    for key in (
        "user.name",
        "user.email",
        "gpg.format",
        "gpg.ssh.program",
        "user.signingkey",
        "gpg.ssh.allowedSignersFile",
    ):
        value = _git(repo, "config", "--get", key, environment=env)
        _git(target, "config", key, value, environment=env)
    _git(target, "config", "commit.gpgsign", "true", environment=env)
    candidate, work = repo.parent / "merge-candidate", repo.parent / "merge-work"
    _git(target, "worktree", "add", "-b", "candidate/dev", str(candidate), environment=env)
    _git(target, "worktree", "add", "-b", "work/merge", str(work), environment=env)
    for root, name in ((work, "lane-contribution"), (candidate, "incoming-contribution")):
        _change(root, name)
        (root / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        _git(root, "add", "README.md", "openspec", environment=env)
        _git(root, "commit", "-m", f"feat: {name}", environment=env)
    ours = _git(work, "rev-parse", "HEAD", environment=env)
    theirs = _git(candidate, "rev-parse", "HEAD", environment=env)
    return target, work, ours, theirs


def prove_native_merge(
    python: Path, repo: Path, *, environment: Mapping[str, str]
) -> dict[str, object]:
    """Execute start, preserved abort, replay and signed continue using only package CLI."""
    actor = "agent:test:package-only:merge"
    env = {**environment, "ETHOS_ACTOR": actor}
    prefix = (str(python), "-B", "-I", "-m", "ethos.cli")

    def command(root: Path, *args: str) -> dict[str, object]:
        code, result, diagnostic = invoke(root, (*prefix, *args), environment=env)
        if code or result.get("verdict") != "pass":
            message = f"package_native_merge_failed:{diagnostic}"
            raise RuntimeError(message)
        return result

    def apply(root: Path, preview: dict[str, object]) -> dict[str, object]:
        return command(root, *shlex.split(str(preview["next_action"]))[1:])

    target, work, ours, theirs = _prepare_fixture(repo, env)
    installed = command(target, "hook", "install", "--root", str(target), "--json")
    activation = installed["data"]
    if not isinstance(activation, dict) or not activation.get("python"):
        message = "package_merge_runtime_missing"
        raise TypeError(message)
    prefix = (str(activation["python"]), "-B", "-I", "-m", "ethos.cli")
    lease = command(
        work,
        "lane",
        "lease",
        "reacquire",
        "--path",
        str(work),
        "--holder-ref",
        actor,
        "--root",
        str(work),
        "--json",
    )
    apply(work, lease)
    refresh = ("lane", "refresh-base", "--strategy", "merge")
    start = command(work, *refresh, "--mode", "start", "--json")
    apply(work, start)
    unique = b"# Valuable partial packaged resolution\n"
    (work / "README.md").write_bytes(unique)
    abort = command(work, *refresh, "--mode", "abort", "--json")
    aborted = apply(work, abort)
    data = aborted["data"]
    if not isinstance(data, dict) or not isinstance(data.get("recovery"), dict):
        message = "package_merge_recovery_missing"
        raise TypeError(message)
    material = json.loads(Path(str(data["recovery"]["path"])).read_text())
    if base64.b64decode(material["files"]["README.md"]["content"]) != unique:
        message = "package_merge_recovery_content_mismatch"
        raise RuntimeError(message)
    apply(work, abort)
    apply(work, command(work, *refresh, "--mode", "start", "--json"))
    command(
        work,
        "lane",
        "prewrite",
        "README.md",
        "--editor-root",
        str(work),
        "--require-editor-root",
        "--root",
        str(work),
        "--json",
    )
    (work / "README.md").write_text("# Accepted packaged resolution\n", encoding="utf-8")
    _git(work, "add", "README.md", environment=env)
    continued = apply(work, command(work, *refresh, "--mode", "continue", "--json"))
    head, *parents = _git(work, "rev-list", "--parents", "-n", "1", "HEAD", environment=env).split()
    if parents != [ours, theirs] or verify_commit_trust(work, head)["verdict"] != "pass":
        message = "package_merge_parents_or_signature_invalid"
        raise RuntimeError(message)
    if _git(work, "status", "--porcelain", environment=env):
        message = "package_merge_dirty_postcondition"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "head": head,
        "parents": parents,
        "continuation_state": continued["state"],
        "recovery_content_verified": True,
        "signature_verified": True,
        "command_runtime_package_only": True,
    }
