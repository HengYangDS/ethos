# ruff: noqa: E501 - the source-budget closeout keeps equivalent envelopes compact.
# fmt: off

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import cast

from ethos.normalization.core import string_list
from ethos.normalization.core import string_mapping
from ethos.repository.adoption.retirement.rollback import rollback_window_checks
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos.repository.profile import AdoptionBoundaryPolicy
from ethos.repository.profile import BackendPolicy
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
RETIREMENT_READY_STATES = {'retirement_ready', 'ready_to_retire', 'retired'}
EXTERNAL_DEFAULT_STATES = RETIREMENT_READY_STATES | {'default', 'rollback_window'}
EMBEDDED_FROZEN_STATES = {'frozen_fallback', 'reference_only', 'retired'}

def retirement_readiness_report(*, target: Path, product_root: Path, parity_gaps: dict[str, object] | None=None, shadow: dict[str, object] | None=None) -> dict[str, object]:
    """Report whether an adopter can retire its embedded ETHOS backend."""
    repo, product = (target.resolve(), product_root.resolve())
    profile = load_repository_profile(repo)
    declaration = profile.declaration
    boundary = declaration.adoption_boundary if declaration else None
    external = declaration.external_backend if declaration else None
    embedded = declaration.embedded_backend if declaration else None
    rollback = declaration.rollback_window if declaration else None
    external_state = external.state if external else ''
    embedded_state = embedded.state if embedded else ''
    parity_ok = bool(parity_gaps and parity_gaps.get('ok') is True)
    shadow_ok = bool(shadow and shadow.get('ok') is True)
    adopter = declaration.profile_id if declaration else repo.name
    checks = {'profile': _profile_checks(repo, profile_exists=profile.exists, profile_valid=profile.state == 'valid'), 'binding': _binding_checks(repo, boundary), 'external_backend': _external_backend_checks(external), 'backend_control': _backend_control_checks(repo, external), 'embedded_backend': _embedded_backend_checks(repo, embedded), 'rollback_window': rollback_window_checks(repo, product, rollback, context={'external_state': external_state, 'embedded_state': embedded_state, 'parity_ok': parity_ok, 'shadow_ok': shadow_ok, 'external_default_states': EXTERNAL_DEFAULT_STATES, 'embedded_frozen_states': EMBEDDED_FROZEN_STATES}), 'product_boundary': _product_boundary_checks(product, boundary), 'docs_topology': _topology_checks(repo, docs=True), 'generated_artifacts': _topology_checks(repo, docs=False), 'parity': _parity_checks(parity_gaps), 'shadow': _shadow_checks(shadow)}
    gaps = [gap for check in checks.values() for gap in string_list(check.get('required_gaps'), drop_empty=True)]
    stage = _lifecycle_stage(external_state=external_state, embedded_state=embedded_state, parity_ok=parity_ok, shadow_ok=shadow_ok)
    if stage != 'retirement_ready':
        gaps.append(f'retirement_lifecycle_incomplete:{stage}')
    gaps = list(dict.fromkeys(gaps))
    return {'ok': not gaps, 'state': 'ready' if not gaps else _report_state(stage, gaps), 'adopter': adopter, 'target': repo.as_posix(), 'product_root': product.as_posix(), 'profile_source': profile.source, 'checks': checks, 'required_gaps': gaps, 'next_actions': _next_actions(adopter, repo, product, gaps)}

def _check(gaps: list[str], **values: object) -> dict[str, object]:
    return {'ok': not gaps, **values, 'required_gaps': gaps}

def _profile_checks(repo: Path, *, profile_exists: bool, profile_valid: bool) -> dict[str, object]:
    gaps = [gap for missing, gap in ((not profile_exists, 'retirement_profile_missing:.ethos/profile.toml'), (not profile_valid, 'retirement_profile_invalid:.ethos/profile.toml')) if missing]
    return _check(gaps, source='.ethos/profile.toml' if profile_exists else '', path=(repo / '.ethos' / 'profile.toml').as_posix())

def _binding_checks(repo: Path, boundary: AdoptionBoundaryPolicy | None) -> dict[str, object]:
    manifest = boundary.binding_manifest if boundary else '.ethos/profile.toml'
    config = boundary.execution_config_root if boundary else '.config'
    gaps = [gap for invalid, gap in ((manifest != '.ethos/profile.toml', f'retirement_binding_manifest_not_generic:{manifest}'), (config != '.config', f'retirement_execution_config_root_not_config:{config}'), (not (repo / manifest).exists(), f'retirement_binding_manifest_missing:{manifest}'), (not (repo / config).exists(), f'retirement_execution_config_root_missing:{config}')) if invalid]
    return _check(gaps, binding_manifest=manifest, execution_config_root=config)

def _external_backend_checks(external: BackendPolicy | None) -> dict[str, object]:
    state = external.state if external else ''
    version = external.minimum_version if external else ''
    shadow_required = external.shadow_required if external else False
    gaps = [gap for invalid, gap in ((external is None, 'retirement_external_backend_missing'), (version != 'external>=embedded', 'retirement_external_minimum_version_not_ge_embedded'), (not shadow_required, 'retirement_shadow_not_required'), (state not in EXTERNAL_DEFAULT_STATES, f"retirement_external_backend_not_default:{state or 'missing'}"), (state not in RETIREMENT_READY_STATES, f"retirement_external_backend_not_retirement_ready:{state or 'missing'}")) if invalid]
    return _check(gaps, state=state, minimum_version=version, shadow_required=shadow_required)

def _backend_control_checks(repo: Path, external: BackendPolicy | None) -> dict[str, object]:
    control = external.control if external else ''
    expected = external.state if external else ''
    if not control:
        return _check([], path='')
    path = repo / control
    if not path.exists():
        return _check([f'retirement_backend_control_missing:{control}'], path=path.as_posix())
    data, parse_gap = _read_backend_control(path, control)
    if parse_gap:
        return _check([parse_gap], path=path.as_posix())
    contract, current = (_table(data, 'contract'), _table(data, 'current'))
    gaps = _backend_control_contract_gaps(contract)
    gaps.extend(_backend_control_current_gaps(current, expected))
    gaps.extend(_backend_control_forbidden_gaps(_table(data, 'forbidden')))
    gaps.extend(_backend_control_rollback_gaps(_table(data, 'rollback_window'), expected))
    return _check(gaps, path=path.as_posix(), **{field: str(current.get(field) or '') for field in ('state', 'default_backend', 'external_backend', 'rollback_mode')})



def _read_backend_control(path: Path, control: str) -> tuple[dict[str, object], str]:
    try:
        return (tomllib.loads(path.read_text(encoding='utf-8')), '')
    except (OSError, tomllib.TOMLDecodeError):
        return ({}, f'retirement_backend_control_invalid:{control}')

def _table(data: dict[str, object], key: str) -> dict[str, object]:
    """Return one string-keyed table without leaking untyped TOML values."""
    return string_mapping(data.get(key))

def _backend_control_contract_gaps(contract: dict[str, object]) -> list[str]:
    asset = str(contract.get('asset_kind') or '')
    binding = str(contract.get('profile_binding') or '')
    return [gap for invalid, gap in ((asset != 'ExternalEthosBackendSwitch', f"retirement_backend_control_asset_kind_invalid:{asset or 'missing'}"), (bool(binding and binding != '.ethos/profile.toml'), f'retirement_backend_control_profile_binding_invalid:{binding}')) if invalid]

def _backend_control_current_gaps(current: dict[str, object], expected_state: str) -> list[str]:
    actual = {field: str(current.get(field) or '') for field in ('state', 'default_backend', 'external_backend', 'rollback_mode')}
    expected = {'state': expected_state, 'default_backend': _expected_default_backend(expected_state), 'external_backend': _expected_control_external_backend(expected_state)}
    labels = {'state': 'state', 'default_backend': 'default', 'external_backend': 'external_backend'}
    gaps = [f"retirement_backend_control_{labels[field]}_mismatch:{value or 'missing'}:{actual[field] or 'missing'}" for field, value in expected.items() if actual[field] != value]
    allowed = {'embedded_fallback'}
    if expected_state == actual['state'] == 'retired':
        allowed.add('git_revert_or_restore_from_history')
    if actual['rollback_mode'] not in allowed:
        gaps.append(f"retirement_backend_control_rollback_mode_invalid:{actual['rollback_mode'] or 'missing'}")
    return gaps

def _backend_control_forbidden_gaps(forbidden: dict[str, object]) -> list[str]:
    return [f'retirement_backend_control_forbidden_not_true:{key}' for key in ('repo_local_execution_wrapper', 'config_script_home', 'adopter_named_external_product_root', 'default_flip_without_rollback_window') if forbidden.get(key) is not True]

def _backend_control_rollback_gaps(rollback: dict[str, object], expected_state: str) -> list[str]:
    state = str(rollback.get('state') or '')
    invalid = expected_state in EXTERNAL_DEFAULT_STATES and expected_state != 'adoption_preview' and (state not in {'planned', 'active', 'complete'})
    return ['retirement_backend_control_rollback_window_not_declared'] if invalid else []

def _embedded_backend_checks(repo: Path, embedded: BackendPolicy | None) -> dict[str, object]:
    state = embedded.state if embedded else ''
    policy = embedded.retirement_policy if embedded else ''
    gaps = [gap for invalid, gap in ((embedded is None, 'retirement_embedded_backend_missing'), (state not in EMBEDDED_FROZEN_STATES, f"retirement_embedded_backend_not_frozen:{state or 'missing'}"), (not policy, 'retirement_policy_missing'), (bool(policy and (not (repo / policy).exists())), f'retirement_policy_path_missing:{policy}')) if invalid]
    return _check(gaps, state=state, retirement_policy=policy)

def _product_boundary_checks(product: Path, boundary: AdoptionBoundaryPolicy | None) -> dict[str, object]:
    forbidden = list(boundary.forbidden_external_product_roots) if boundary else []
    present = [path for path in forbidden if (product / path).exists()]
    gaps = [f'forbidden_external_product_root_present:{path}' for path in present]
    return _check(gaps, forbidden_external_product_roots=forbidden, present_forbidden_roots=present)

def _topology_checks(repo: Path, *, docs: bool) -> dict[str, object]:
    report = docs_topology_report(repo) if docs else generated_artifact_topology_report(repo)
    prefix = 'retirement_docs_topology' if docs else 'retirement_generated_artifacts'
    gaps = [f'{prefix}:{gap}' for gap in string_list(report.get('required_gaps'), drop_empty=True)]
    summary = string_mapping(report.get('summary'))
    fields = ('missing_paths', 'forbidden_roots') if docs else ('allowed_paths', 'denied_paths', 'review_paths')
    counts = ('required_path_count', 'missing_required_path_count') if docs else ('allowed_path_count', 'denied_path_count', 'review_path_count', 'review_gap_count')
    values: dict[str, object] = {'state': report.get('state', ''), **{field: string_list(report.get(field), drop_empty=True) for field in fields}}
    return _check(gaps, **values, summary={field: summary.get(field, 0) for field in counts})

def _parity_checks(parity: dict[str, object] | None) -> dict[str, object]:
    if parity is None:
        return _check(['retirement_parity_gaps_not_checked'])
    gaps = string_list(parity.get('required_gaps'), drop_empty=True)
    if parity.get('ok') is not True and (not gaps):
        gaps.append('retirement_parity_not_clean')
    return _check([f'retirement_parity:{gap}' for gap in gaps], summary={'adopter': parity.get('adopter', ''), 'pending_package_count': len(_object_list(parity.get('pending_packages')))})

def _shadow_checks(shadow: dict[str, object] | None) -> dict[str, object]:
    if shadow is None:
        return _check(['retirement_shadow_not_checked'])
    gaps = string_list(shadow.get('required_gaps'), drop_empty=True)
    false_negatives = _int_value(shadow.get('false_negative_count'))
    if shadow.get('ok') is not True and (not gaps):
        gaps.append('retirement_shadow_not_matched')
    if false_negatives:
        gaps.append(f'retirement_shadow_false_negative_count:{false_negatives}')
    return _check([f'retirement_shadow:{gap}' for gap in gaps], summary={'state': shadow.get('state', ''), 'false_negative_count': false_negatives, 'accepted_summary': shadow.get('accepted_summary', {})})

def _expected_default_backend(external_state: str) -> str:
    return 'external' if external_state in EXTERNAL_DEFAULT_STATES else 'embedded'

def _expected_control_external_backend(external_state: str) -> str:
    return 'retirement_ready' if external_state in RETIREMENT_READY_STATES else 'default' if external_state in EXTERNAL_DEFAULT_STATES else 'preview'

def _report_state(stage: str, gaps: list[str]) -> str:
    for prefix, state in (('retirement_docs_topology:', 'docs_topology_open'), ('retirement_generated_artifacts:', 'generated_artifacts_open'), ('retirement_backend_control_', 'backend_control_open'), ('retirement_rollback_window_', 'rollback_window_evidence_open')):
        if any(gap.startswith(prefix) for gap in gaps):
            return state
    return stage

def _lifecycle_stage(*, external_state: str, embedded_state: str, parity_ok: bool, shadow_ok: bool) -> str:
    for incomplete, state in ((not parity_ok, 'parity_open'), (not shadow_ok, 'shadow_open'), (external_state not in EXTERNAL_DEFAULT_STATES, 'external_not_default'), (embedded_state not in EMBEDDED_FROZEN_STATES, 'embedded_not_frozen'), (external_state not in RETIREMENT_READY_STATES, 'rollback_window')):
        if incomplete:
            return state
    return 'retirement_ready'

def _next_actions(adopter: str, repo: Path, product: Path, gaps: list[str]) -> list[str]:
    if not gaps:
        return ['record separate Retirement Decision before removing embedded backend']
    parity_action = f'ethos parity shadow --adopter {adopter} --target {repo.as_posix()} --execute --write-evidence --json'
    specs: tuple[tuple[Callable[[str], bool], str], ...] = ((lambda gap: gap.startswith(('retirement_parity', 'retirement_shadow', 'retirement_lifecycle_incomplete:parity_open', 'retirement_lifecycle_incomplete:shadow_open')), parity_action), (lambda gap: gap.startswith('retirement_external_backend_not_default'), 'switch adopter default backend to external under a reversible control'), (lambda gap: gap.startswith('retirement_embedded_backend_not_frozen'), 'freeze embedded backend as fallback/reference during rollback window'), (lambda gap: gap.startswith('retirement_docs_topology:'), f'ethos quality docs-topology --root {repo.as_posix()} --json'), (lambda gap: gap.startswith('retirement_generated_artifacts:'), f'ethos quality generated-artifacts --root {repo.as_posix()} --json'), (lambda gap: gap.startswith('retirement_backend_control_'), 'repair the profile-declared external-ethos-backend control manifest'), (lambda gap: gap.startswith('retirement_rollback_window_'), 'populate [rollback_window] with a manifest and completed proof_report, work_lane_closeout, domain_gate, and assistant_playbook scenarios'), (lambda gap: gap.startswith('retirement_lifecycle_incomplete:rollback_window'), 'record rollback-window evidence for proof/report, Work Lane, domain gate, and playbook paths'))
    actions = [action for matches, action in specs if any(matches(gap) for gap in gaps)]
    actions.append(f'ethos fleet retirement-readiness --target {repo.as_posix()} --root {product.as_posix()} --json')
    return list(dict.fromkeys(actions))

def _object_list(value: object) -> list[object]:
    return cast('list[object]', value) if isinstance(value, list) else []

def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    try:
        return int(value) if isinstance(value, str) else 0
    except ValueError:
        return 0
