"""Shared parity test snapshots and repository fixtures."""

from __future__ import annotations

import hashlib
import subprocess
from typing import TYPE_CHECKING

from ethos.repository.evidence.parity.validation import SHADOW_PARITY_COMMANDS

if TYPE_CHECKING:
    from pathlib import Path

MIGRATED_CAPABILITIES = [
    "work-lane-lifecycle",
    "proof-evidence-chronicle",
    "campaign-hypothesis-evolution",
    "assistant-playbooks-skills",
    "quality-determinism-local-state",
    "openspec-claims-trust-review",
]

SHADOW_COMMANDS = list(SHADOW_PARITY_COMMANDS)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "dev"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "init",
        ],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def git_head(path: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def complete_parity_evidence(adopter: str) -> dict[str, object]:
    command = (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target /workspace/{adopter} --execute --timeout-seconds 30 --json"
    )
    return {
        "schema_version": 1,
        "adopter": adopter,
        "target": f"/workspace/{adopter}",
        "generated_on": "2026-07-01",
        "command": command,
        "freshness": {
            "product_head": "product-head",
            "target_head": "target-head",
            "command_sha256": sha256_text(command),
        },
        "shadow": {
            "ok": True,
            "required_gaps": [],
            "comparison_count": len(SHADOW_COMMANDS),
            "commands": SHADOW_COMMANDS,
            "false_negative_count": 0,
        },
        "semantic_dimensions": ["blocking_vs_advisory", "external_false_negative"],
        "verified_capabilities": MIGRATED_CAPABILITIES,
        "capability_basis": {
            capability: [f"{capability} shadow parity basis"]
            for capability in MIGRATED_CAPABILITIES
        },
    }


def retarget_parity_evidence(
    evidence: dict[str, object],
    *,
    adopter: str,
    target: Path,
    timeout_seconds: int = 30,
) -> None:
    command = (
        f"uv run --package ethos ethos parity shadow --adopter {adopter} "
        f"--target {target.resolve().as_posix()} --execute "
        f"--timeout-seconds {timeout_seconds} --json"
    )
    evidence["target"] = target.resolve().as_posix()
    evidence["command"] = command
    freshness = evidence["freshness"]
    assert isinstance(freshness, dict)
    freshness["command_sha256"] = sha256_text(command)
