from __future__ import annotations

import subprocess
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from ethos_core.normalization.core import string_mapping

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.profile import RollbackWindowPolicy

STANDARD_ROLLBACK_SCENARIOS = (
    "proof_report",
    "work_lane_closeout",
    "domain_gate",
    "assistant_playbook",
)


def rollback_window_checks(
    repo: Path,
    product: Path,
    rollback_window: RollbackWindowPolicy | None,
    *,
    context: dict[str, object],
) -> dict[str, object]:
    external_state = str(context.get("external_state") or "")
    embedded_state = str(context.get("embedded_state") or "")
    external_default_states = set(cast("set[str]", context.get("external_default_states") or set()))
    embedded_frozen_states = set(cast("set[str]", context.get("embedded_frozen_states") or set()))
    applicable = (
        context.get("parity_ok") is True
        and context.get("shadow_ok") is True
        and external_state in external_default_states
        and embedded_state in embedded_frozen_states
    )
    configured_required = list(rollback_window.required_scenarios) if rollback_window else []
    required_scenarios = list(dict.fromkeys((*STANDARD_ROLLBACK_SCENARIOS, *configured_required)))
    completed_scenarios = list(rollback_window.completed_scenarios) if rollback_window else []
    evidence_manifest = rollback_window.evidence_manifest if rollback_window else ""
    state = rollback_window.state if rollback_window else ""
    gaps = []
    if applicable:
        if rollback_window is None:
            gaps.append("retirement_rollback_window_missing")
        if state != "complete":
            gaps.append(f"retirement_rollback_window_not_complete:{state or 'missing'}")
        if not evidence_manifest:
            gaps.append("retirement_rollback_window_evidence_manifest_missing")
        else:
            gaps.extend(
                rollback_manifest_gaps(
                    repo=repo,
                    product=product,
                    evidence_manifest=evidence_manifest,
                    required_scenarios=required_scenarios,
                )
            )
        completed = set(completed_scenarios)
        gaps.extend(
            f"retirement_rollback_window_scenario_missing:{scenario}"
            for scenario in required_scenarios
            if scenario not in completed
        )
    return {
        "ok": not gaps,
        "applicable": applicable,
        "state": state,
        "evidence_manifest": evidence_manifest,
        "standard_scenarios": list(STANDARD_ROLLBACK_SCENARIOS),
        "required_scenarios": required_scenarios,
        "completed_scenarios": completed_scenarios,
        "required_gaps": gaps,
    }


def rollback_manifest_gaps(
    *,
    repo: Path,
    product: Path,
    evidence_manifest: str,
    required_scenarios: list[str],
) -> list[str]:
    gaps: list[str] = []
    manifest_path = repo_relative_path(repo, evidence_manifest)
    if manifest_path is None:
        return [
            f"retirement_rollback_window_evidence_manifest_path_outside_repo:{evidence_manifest}"
        ]
    if not manifest_path.exists():
        return [f"retirement_rollback_window_evidence_manifest_path_missing:{evidence_manifest}"]
    if not git_tracked(repo, evidence_manifest):
        gaps.append(f"retirement_rollback_window_evidence_manifest_not_tracked:{evidence_manifest}")

    manifest, manifest_gaps = load_rollback_manifest(manifest_path, evidence_manifest)
    gaps.extend(manifest_gaps)
    if manifest is None:
        return gaps

    gaps.extend(rollback_manifest_head_gaps(repo, product, manifest))
    gaps.extend(
        rollback_manifest_required_scenario_gaps(
            repo=repo,
            evidence_manifest=evidence_manifest,
            manifest=manifest,
            required_scenarios=required_scenarios,
        )
    )
    return gaps


def load_rollback_manifest(
    manifest_path: Path, evidence_manifest: str
) -> tuple[dict[str, object] | None, list[str]]:
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None, [f"retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}"]
    if not manifest:
        return None, [f"retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}"]
    return cast("dict[str, object]", manifest), []


def rollback_manifest_head_gaps(
    repo: Path, product: Path, manifest: dict[str, object]
) -> list[str]:
    gaps: list[str] = []
    target_head = str(manifest.get("target_head") or "")
    product_head = str(manifest.get("product_head") or "")
    if not git_commit_reachable(repo, target_head):
        gaps.append(
            "retirement_rollback_window_evidence_manifest_target_head_unreachable:"
            f"{target_head or 'missing'}"
        )
    if not git_commit_reachable(product, product_head):
        gaps.append(
            "retirement_rollback_window_evidence_manifest_product_head_unreachable:"
            f"{product_head or 'missing'}"
        )
    return gaps


def rollback_manifest_required_scenario_gaps(
    *,
    repo: Path,
    evidence_manifest: str,
    manifest: dict[str, object],
    required_scenarios: list[str],
) -> list[str]:
    gaps: list[str] = []
    target_head = str(manifest.get("target_head") or "")
    product_head = str(manifest.get("product_head") or "")
    raw_scenarios = manifest.get("scenarios")
    if not isinstance(raw_scenarios, dict):
        gaps.append(f"retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}")
    scenarios = string_mapping(raw_scenarios)

    for scenario in required_scenarios:
        payload = string_mapping(scenarios.get(scenario))
        if not payload:
            gaps.append(f"retirement_rollback_window_manifest_scenario_missing:{scenario}")
            continue
        gaps.extend(
            rollback_manifest_scenario_gaps(
                repo=repo,
                scenario=scenario,
                payload=payload,
                target_head=target_head,
                product_head=product_head,
            )
        )
    return gaps


def rollback_manifest_scenario_gaps(
    *,
    repo: Path,
    scenario: str,
    payload: dict[str, object],
    target_head: str,
    product_head: str,
) -> list[str]:
    gaps: list[str] = []
    if str(payload.get("target_head") or "") != target_head:
        gaps.append(f"retirement_rollback_window_manifest_scenario_target_head_mismatch:{scenario}")
    if str(payload.get("product_head") or "") != product_head:
        gaps.append(
            f"retirement_rollback_window_manifest_scenario_product_head_mismatch:{scenario}"
        )
    if not str(payload.get("command") or ""):
        gaps.append(f"retirement_rollback_window_manifest_scenario_command_missing:{scenario}")
    if not str(payload.get("digest") or ""):
        gaps.append(f"retirement_rollback_window_manifest_scenario_digest_missing:{scenario}")

    evidence = str(payload.get("evidence") or "")
    evidence_path = repo_relative_path(repo, evidence)
    if not evidence:
        gaps.append(f"retirement_rollback_window_manifest_scenario_evidence_missing:{scenario}")
    elif evidence_path is None:
        gaps.append(
            f"retirement_rollback_window_manifest_scenario_evidence_outside_repo:{scenario}"
        )
    elif not evidence_path.exists():
        gaps.append(
            f"retirement_rollback_window_manifest_scenario_evidence_path_missing:"
            f"{scenario}:{evidence}"
        )
    elif not git_tracked(repo, evidence):
        gaps.append(
            f"retirement_rollback_window_manifest_scenario_evidence_not_tracked:"
            f"{scenario}:{evidence}"
        )
    return gaps


def repo_relative_path(repo: Path, path: str) -> Path | None:
    if not path or path.startswith(("/", "~")):
        return None
    resolved = (repo / path).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        return None
    return resolved


def git_tracked(repo: Path, path: str) -> bool:
    if repo_relative_path(repo, path) is None:
        return False
    result = subprocess.run(
        ["git", "-C", repo.as_posix(), "ls-files", "--error-unmatch", "--", path],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def git_commit_reachable(repo: Path, commit: str) -> bool:
    if not commit:
        return False
    exists = subprocess.run(
        ["git", "-C", repo.as_posix(), "cat-file", "-e", f"{commit}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if exists.returncode != 0:
        return False
    ancestor = subprocess.run(
        ["git", "-C", repo.as_posix(), "merge-base", "--is-ancestor", commit, "HEAD"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return ancestor.returncode == 0
