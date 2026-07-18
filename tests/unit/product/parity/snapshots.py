"""Shared parity test snapshots and repository fixtures."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.evidence.parity.validation import SHADOW_PARITY_COMMANDS

if TYPE_CHECKING:
    from collections.abc import Callable
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

ACCEPTED_DIFFERENCE_REASONS = {
    "external_required_gap_superset": "external product reports the embedded blocking gaps plus stricter required gaps",
    "external_stricter_required_gap": "external product reports a stricter blocking gap allowed by shadow parity",
    "external_stricter_plan_scope": "external product plans a stricter changed-scope gate set allowed by shadow parity",
}


def parity_payload(
    command: str,
    *,
    ok: bool,
    state: object,
    gaps: tuple[str, ...] = (),
    **fields: object,
) -> dict[str, object]:
    return {"ok": ok, "command": command, "state": state, "required_gaps": list(gaps), **fields}


def accepted_difference(
    kind: str,
    command: str,
    gaps: tuple[str, ...],
) -> list[dict[str, object]]:
    return [
        {
            "kind": kind,
            "classification": "accepted",
            "scope": kind,
            "commands": [f"ethos {command}"],
            "gaps": list(gaps),
            "reason": ACCEPTED_DIFFERENCE_REASONS[kind],
        }
    ]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def successful_shadow_popen(
    calls: list[tuple[list[str], Path]],
    *,
    reported_command: str = "status",
) -> Callable[..., object]:
    """Return an inert successful shadow process and record its invocation."""

    class Process:
        returncode = 0

        def __init__(self, command: list[str]) -> None:
            self.command = command

        def communicate(self, timeout: int | None = None) -> tuple[str, str]:
            _ = timeout
            return json.dumps({"ok": True, "command": reported_command, "state": "ready"}), ""

    def fake_popen(command: list[str], **kwargs: Any) -> Process:
        calls.append((command, kwargs["cwd"]))
        return Process(command)

    return fake_popen


def checkout_work_lane(repo: Path) -> None:
    """Put a fixture repository in its deterministic parity-evidence Work Lane."""
    subprocess.run(
        ["git", "checkout", "-b", "work/parity-evidence"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        subject="work/parity-evidence",
        holder_ref="agent:codex:thread:parity-evidence",
        payload={"expected_head": git_head(repo)},
    )


def write_parity_evidence(
    root: Path,
    evidence: dict[str, object],
    *,
    adopter: str = "sample-adopter",
) -> Path:
    path = root / "evidence" / "parity" / f"{adopter}-shadow.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence), encoding="utf-8")
    return path


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


def set_durable_evidence_root(repo: Path, value: str) -> None:
    """Configure and commit the fixture's durable evidence root."""
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(f'[roots]\ndurable_evidence = "{value}"\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "configure evidence root",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
    )


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
