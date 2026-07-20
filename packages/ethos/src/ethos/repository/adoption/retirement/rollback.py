# ruff: noqa: E501 - the source-budget closeout keeps equivalent envelopes compact.
# fmt: off

from __future__ import annotations

import subprocess
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from ethos_core.normalization.core import string_mapping

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.profile import RollbackWindowPolicy
STANDARD_ROLLBACK_SCENARIOS = ('proof_report', 'work_lane_closeout', 'domain_gate', 'assistant_playbook')

def rollback_window_checks(repo: Path, product: Path, rollback_window: RollbackWindowPolicy | None, *, context: dict[str, object]) -> dict[str, object]:
    external_state, embedded_state = (str(context.get('external_state') or ''), str(context.get('embedded_state') or ''))
    applicable = all((context.get('parity_ok') is True, context.get('shadow_ok') is True, external_state in set(cast('set[str]', context.get('external_default_states') or set())), embedded_state in set(cast('set[str]', context.get('embedded_frozen_states') or set()))))
    configured = list(rollback_window.required_scenarios) if rollback_window else []
    required = list(dict.fromkeys((*STANDARD_ROLLBACK_SCENARIOS, *configured)))
    completed = list(rollback_window.completed_scenarios) if rollback_window else []
    manifest = rollback_window.evidence_manifest if rollback_window else ''
    state = rollback_window.state if rollback_window else ''
    gaps: list[str] = []
    if applicable:
        gaps.extend((gap for invalid, gap in ((rollback_window is None, 'retirement_rollback_window_missing'), (state != 'complete', f"retirement_rollback_window_not_complete:{state or 'missing'}"), (not manifest, 'retirement_rollback_window_evidence_manifest_missing')) if invalid))
        if manifest:
            gaps.extend(rollback_manifest_gaps(repo=repo, product=product, evidence_manifest=manifest, required_scenarios=required))
        gaps.extend(f'retirement_rollback_window_scenario_missing:{scenario}' for scenario in required if scenario not in set(completed))
    return {'ok': not gaps, 'applicable': applicable, 'state': state, 'evidence_manifest': manifest, 'standard_scenarios': list(STANDARD_ROLLBACK_SCENARIOS), 'required_scenarios': required, 'completed_scenarios': completed, 'required_gaps': gaps}

def rollback_manifest_gaps(*, repo: Path, product: Path, evidence_manifest: str, required_scenarios: list[str]) -> list[str]:
    path = repo_relative_path(repo, evidence_manifest)
    if path is None:
        return [f'retirement_rollback_window_evidence_manifest_path_outside_repo:{evidence_manifest}']
    if not path.exists():
        return [f'retirement_rollback_window_evidence_manifest_path_missing:{evidence_manifest}']
    gaps = [] if git_tracked(repo, evidence_manifest) else [f'retirement_rollback_window_evidence_manifest_not_tracked:{evidence_manifest}']
    manifest, manifest_gaps = load_rollback_manifest(path, evidence_manifest)
    gaps.extend(manifest_gaps)
    if manifest is not None:
        gaps.extend(rollback_manifest_head_gaps(repo, product, manifest))
        gaps.extend(rollback_manifest_required_scenario_gaps(repo=repo, evidence_manifest=evidence_manifest, manifest=manifest, required_scenarios=required_scenarios))
    return gaps

def load_rollback_manifest(manifest_path: Path, evidence_manifest: str) -> tuple[dict[str, object] | None, list[str]]:
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError:
        manifest = {}
    gap = f'retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}'
    return (cast('dict[str, object]', manifest), []) if manifest else (None, [gap])

def rollback_manifest_head_gaps(repo: Path, product: Path, manifest: dict[str, object]) -> list[str]:
    return [f"retirement_rollback_window_evidence_manifest_{kind}_head_unreachable:{head or 'missing'}" for root, kind, head in ((repo, 'target', str(manifest.get('target_head') or '')), (product, 'product', str(manifest.get('product_head') or ''))) if not git_commit_reachable(root, head)]

def rollback_manifest_required_scenario_gaps(*, repo: Path, evidence_manifest: str, manifest: dict[str, object], required_scenarios: list[str]) -> list[str]:
    raw = manifest.get('scenarios')
    gaps = [] if isinstance(raw, dict) else [f'retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}']
    scenarios = string_mapping(raw)
    target, product = (str(manifest.get('target_head') or ''), str(manifest.get('product_head') or ''))
    for scenario in required_scenarios:
        payload = string_mapping(scenarios.get(scenario))
        if not payload:
            gaps.append(f'retirement_rollback_window_manifest_scenario_missing:{scenario}')
        else:
            gaps.extend(rollback_manifest_scenario_gaps(repo=repo, scenario=scenario, payload=payload, target_head=target, product_head=product))
    return gaps

def rollback_manifest_scenario_gaps(*, repo: Path, scenario: str, payload: dict[str, object], target_head: str, product_head: str) -> list[str]:
    gaps = [f'retirement_rollback_window_manifest_scenario_{field}_head_mismatch:{scenario}' for field, expected in (('target', target_head), ('product', product_head)) if str(payload.get(f'{field}_head') or '') != expected]
    gaps.extend(f'retirement_rollback_window_manifest_scenario_{field}_missing:{scenario}' for field in ('command', 'digest') if not str(payload.get(field) or ''))
    evidence = str(payload.get('evidence') or '')
    path = repo_relative_path(repo, evidence)
    if not evidence:
        gaps.append(f'retirement_rollback_window_manifest_scenario_evidence_missing:{scenario}')
    elif path is None:
        gaps.append(f'retirement_rollback_window_manifest_scenario_evidence_outside_repo:{scenario}')
    elif not path.exists():
        gaps.append(f'retirement_rollback_window_manifest_scenario_evidence_path_missing:{scenario}:{evidence}')
    elif not git_tracked(repo, evidence):
        gaps.append(f'retirement_rollback_window_manifest_scenario_evidence_not_tracked:{scenario}:{evidence}')
    return gaps

def repo_relative_path(repo: Path, path: str) -> Path | None:
    if not path or path.startswith(('/', '~')):
        return None
    resolved = (repo / path).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        return None
    else:
        return resolved

def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(['git', '-C', repo.as_posix(), *args], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def git_tracked(repo: Path, path: str) -> bool:
    return repo_relative_path(repo, path) is not None and _git_ok(repo, 'ls-files', '--error-unmatch', '--', path)

def git_commit_reachable(repo: Path, commit: str) -> bool:
    return bool(commit and _git_ok(repo, 'cat-file', '-e', f'{commit}^{{commit}}') and _git_ok(repo, 'merge-base', '--is-ancestor', commit, 'HEAD'))
