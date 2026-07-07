from __future__ import annotations

import subprocess
import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.policy.docs_topology import docs_topology_report
from ethos.repository.profile import load_repository_profile

RETIREMENT_READY_STATES = {"retirement_ready", "ready_to_retire", "retired"}
EXTERNAL_DEFAULT_STATES = RETIREMENT_READY_STATES | {"default", "rollback_window"}
EMBEDDED_FROZEN_STATES = {"frozen_fallback", "reference_only", "retired"}
STANDARD_ROLLBACK_SCENARIOS = (
    "proof_report",
    "work_lane_closeout",
    "domain_gate",
    "assistant_playbook",
)


def retirement_readiness_report(
    *,
    target: Path,
    product_root: Path,
    parity_gaps: dict[str, object] | None = None,
    shadow: dict[str, object] | None = None,
) -> dict[str, object]:
    """Report whether an adopter can retire its embedded ETHOS backend.

    This is intentionally profile-driven. Product ETHOS may inspect an adopter
    profile and evidence, but it must not learn a product-core directory such as
    ``adopters/<name>`` or ``profiles/<name>`` for one repository.
    """

    repo = target.resolve()
    product = product_root.resolve()
    profile = load_repository_profile(repo)
    required_gaps: list[str] = []

    if not profile.exists:
        required_gaps.append("retirement_profile_missing:.ethos/profile.toml")
    if not profile.valid:
        required_gaps.append("retirement_profile_invalid:.ethos/profile.toml")

    adoption_boundary = profile.tables.get("adoption_boundary", {})
    external_backend = profile.tables.get("external_backend", {})
    embedded_backend = profile.tables.get("embedded_backend", {})
    rollback_window = profile.tables.get("rollback_window", {})

    external_state = str(external_backend.get("state") or "")
    embedded_state = str(embedded_backend.get("state") or "")
    parity_ok = bool(parity_gaps and parity_gaps.get("ok") is True)
    shadow_ok = bool(shadow and shadow.get("ok") is True)

    adopter = profile.identity.get("profile_id") or repo.name
    checks = {
        "profile": _profile_checks(
            repo, profile_exists=profile.exists, profile_valid=profile.valid
        ),
        "binding": _binding_checks(repo, adoption_boundary),
        "external_backend": _external_backend_checks(external_backend),
        "embedded_backend": _embedded_backend_checks(repo, embedded_backend),
        "rollback_window": _rollback_window_checks(
            repo,
            product,
            rollback_window,
            context={
                "external_state": external_state,
                "embedded_state": embedded_state,
                "parity_ok": parity_ok,
                "shadow_ok": shadow_ok,
            },
        ),
        "product_boundary": _product_boundary_checks(product, adoption_boundary),
        "docs_topology": _docs_topology_checks(repo),
        "parity": _parity_checks(parity_gaps),
        "shadow": _shadow_checks(shadow),
    }
    for check in checks.values():
        required_gaps.extend(_string_list(check.get("required_gaps")))

    lifecycle_stage = _lifecycle_stage(
        external_state=external_state,
        embedded_state=embedded_state,
        parity_ok=parity_ok,
        shadow_ok=shadow_ok,
    )
    if lifecycle_stage != "retirement_ready":
        required_gaps.append(f"retirement_lifecycle_incomplete:{lifecycle_stage}")

    required_gaps = list(dict.fromkeys(required_gaps))
    return {
        "ok": not required_gaps,
        "state": "ready" if not required_gaps else _report_state(lifecycle_stage, required_gaps),
        "adopter": adopter,
        "target": repo.as_posix(),
        "product_root": product.as_posix(),
        "profile_source": profile.source,
        "checks": checks,
        "required_gaps": required_gaps,
        "next_actions": _next_actions(adopter, repo, product, required_gaps),
    }


def _profile_checks(repo: Path, *, profile_exists: bool, profile_valid: bool) -> dict[str, object]:
    gaps = []
    if not profile_exists:
        gaps.append("retirement_profile_missing:.ethos/profile.toml")
    if not profile_valid:
        gaps.append("retirement_profile_invalid:.ethos/profile.toml")
    return {
        "ok": not gaps,
        "source": ".ethos/profile.toml" if profile_exists else "",
        "path": (repo / ".ethos" / "profile.toml").as_posix(),
        "required_gaps": gaps,
    }


def _binding_checks(repo: Path, adoption_boundary: dict[str, Any]) -> dict[str, object]:
    binding_manifest = str(adoption_boundary.get("binding_manifest") or ".ethos/profile.toml")
    execution_config_root = str(adoption_boundary.get("execution_config_root") or ".config")
    gaps = []
    if binding_manifest != ".ethos/profile.toml":
        gaps.append(f"retirement_binding_manifest_not_generic:{binding_manifest}")
    if execution_config_root != ".config":
        gaps.append(f"retirement_execution_config_root_not_config:{execution_config_root}")
    if not (repo / binding_manifest).exists():
        gaps.append(f"retirement_binding_manifest_missing:{binding_manifest}")
    if not (repo / execution_config_root).exists():
        gaps.append(f"retirement_execution_config_root_missing:{execution_config_root}")
    return {
        "ok": not gaps,
        "binding_manifest": binding_manifest,
        "execution_config_root": execution_config_root,
        "required_gaps": gaps,
    }


def _external_backend_checks(external_backend: dict[str, Any]) -> dict[str, object]:
    state = str(external_backend.get("state") or "")
    minimum_version = str(external_backend.get("minimum_version") or "")
    shadow_required = external_backend.get("shadow_required") is True
    gaps = []
    if not external_backend:
        gaps.append("retirement_external_backend_missing")
    if minimum_version != "external>=embedded":
        gaps.append("retirement_external_minimum_version_not_ge_embedded")
    if not shadow_required:
        gaps.append("retirement_shadow_not_required")
    if state not in EXTERNAL_DEFAULT_STATES:
        gaps.append(f"retirement_external_backend_not_default:{state or 'missing'}")
    if state not in RETIREMENT_READY_STATES:
        gaps.append(f"retirement_external_backend_not_retirement_ready:{state or 'missing'}")
    return {
        "ok": not gaps,
        "state": state,
        "minimum_version": minimum_version,
        "shadow_required": shadow_required,
        "required_gaps": gaps,
    }


def _embedded_backend_checks(repo: Path, embedded_backend: dict[str, Any]) -> dict[str, object]:
    state = str(embedded_backend.get("state") or "")
    policy = str(embedded_backend.get("retirement_policy") or "")
    gaps = []
    if not embedded_backend:
        gaps.append("retirement_embedded_backend_missing")
    if state not in EMBEDDED_FROZEN_STATES:
        gaps.append(f"retirement_embedded_backend_not_frozen:{state or 'missing'}")
    if not policy:
        gaps.append("retirement_policy_missing")
    elif not (repo / policy).exists():
        gaps.append(f"retirement_policy_path_missing:{policy}")
    return {
        "ok": not gaps,
        "state": state,
        "retirement_policy": policy,
        "required_gaps": gaps,
    }


def _rollback_window_checks(
    repo: Path,
    product: Path,
    rollback_window: dict[str, Any],
    *,
    context: dict[str, object],
) -> dict[str, object]:
    external_state = str(context.get("external_state") or "")
    embedded_state = str(context.get("embedded_state") or "")
    applicable = (
        context.get("parity_ok") is True
        and context.get("shadow_ok") is True
        and external_state in EXTERNAL_DEFAULT_STATES
        and embedded_state in EMBEDDED_FROZEN_STATES
    )
    configured_required = _string_list(rollback_window.get("required_scenarios"))
    required_scenarios = list(dict.fromkeys((*STANDARD_ROLLBACK_SCENARIOS, *configured_required)))
    completed_scenarios = _string_list(rollback_window.get("completed_scenarios"))
    evidence_manifest = str(rollback_window.get("evidence_manifest") or "")
    state = str(rollback_window.get("state") or "")
    gaps = []
    if applicable:
        if not rollback_window:
            gaps.append("retirement_rollback_window_missing")
        if state != "complete":
            gaps.append(f"retirement_rollback_window_not_complete:{state or 'missing'}")
        if not evidence_manifest:
            gaps.append("retirement_rollback_window_evidence_manifest_missing")
        else:
            gaps.extend(
                _rollback_manifest_gaps(
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


def _rollback_manifest_gaps(
    *,
    repo: Path,
    product: Path,
    evidence_manifest: str,
    required_scenarios: list[str],
) -> list[str]:
    gaps: list[str] = []
    manifest_path = _repo_relative_path(repo, evidence_manifest)
    if manifest_path is None:
        return [
            f"retirement_rollback_window_evidence_manifest_path_outside_repo:{evidence_manifest}"
        ]
    if not manifest_path.exists():
        return [f"retirement_rollback_window_evidence_manifest_path_missing:{evidence_manifest}"]
    if not _git_tracked(repo, evidence_manifest):
        gaps.append(f"retirement_rollback_window_evidence_manifest_not_tracked:{evidence_manifest}")

    manifest, manifest_gaps = _load_rollback_manifest(manifest_path, evidence_manifest)
    gaps.extend(manifest_gaps)
    if manifest is None:
        return gaps

    gaps.extend(_rollback_manifest_head_gaps(repo, product, manifest))
    gaps.extend(
        _rollback_manifest_required_scenario_gaps(
            repo=repo,
            evidence_manifest=evidence_manifest,
            manifest=manifest,
            required_scenarios=required_scenarios,
        )
    )
    return gaps


def _load_rollback_manifest(
    manifest_path: Path, evidence_manifest: str
) -> tuple[dict[str, object] | None, list[str]]:
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None, [f"retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}"]
    if not manifest:
        return None, [f"retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}"]
    return cast("dict[str, object]", manifest), []


def _rollback_manifest_head_gaps(
    repo: Path, product: Path, manifest: dict[str, object]
) -> list[str]:
    gaps: list[str] = []
    target_head = str(manifest.get("target_head") or "")
    product_head = str(manifest.get("product_head") or "")
    if not _git_commit_reachable(repo, target_head):
        gaps.append(
            "retirement_rollback_window_evidence_manifest_target_head_unreachable:"
            f"{target_head or 'missing'}"
        )
    if not _git_commit_reachable(product, product_head):
        gaps.append(
            "retirement_rollback_window_evidence_manifest_product_head_unreachable:"
            f"{product_head or 'missing'}"
        )
    return gaps


def _rollback_manifest_required_scenario_gaps(
    *,
    repo: Path,
    evidence_manifest: str,
    manifest: dict[str, object],
    required_scenarios: list[str],
) -> list[str]:
    gaps: list[str] = []
    target_head = str(manifest.get("target_head") or "")
    product_head = str(manifest.get("product_head") or "")
    scenarios = manifest.get("scenarios")
    if not isinstance(scenarios, dict):
        gaps.append(f"retirement_rollback_window_evidence_manifest_invalid:{evidence_manifest}")
        scenarios = {}

    for scenario in required_scenarios:
        payload = scenarios.get(scenario)
        if not isinstance(payload, dict):
            gaps.append(f"retirement_rollback_window_manifest_scenario_missing:{scenario}")
            continue
        gaps.extend(
            _rollback_manifest_scenario_gaps(
                repo=repo,
                scenario=scenario,
                payload=payload,
                target_head=target_head,
                product_head=product_head,
            )
        )
    return gaps


def _rollback_manifest_scenario_gaps(
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
    evidence_path = _repo_relative_path(repo, evidence)
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
    elif not _git_tracked(repo, evidence):
        gaps.append(
            f"retirement_rollback_window_manifest_scenario_evidence_not_tracked:"
            f"{scenario}:{evidence}"
        )
    return gaps


def _product_boundary_checks(
    product_root: Path, adoption_boundary: dict[str, Any]
) -> dict[str, object]:
    forbidden = _string_list(adoption_boundary.get("forbidden_external_product_roots"))
    present = [path for path in forbidden if (product_root / path).exists()]
    gaps = [f"forbidden_external_product_root_present:{path}" for path in present]
    return {
        "ok": not gaps,
        "forbidden_external_product_roots": forbidden,
        "present_forbidden_roots": present,
        "required_gaps": gaps,
    }


def _docs_topology_checks(repo: Path) -> dict[str, object]:
    report = docs_topology_report(repo)
    gaps = [f"retirement_docs_topology:{gap}" for gap in _string_list(report.get("required_gaps"))]
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "ok": not gaps,
        "state": report.get("state", ""),
        "missing_paths": _string_list(report.get("missing_paths")),
        "required_gaps": gaps,
        "summary": {
            "required_path_count": summary.get("required_path_count", 0),
            "missing_required_path_count": summary.get("missing_required_path_count", 0),
        },
    }


def _parity_checks(parity_gaps: dict[str, object] | None) -> dict[str, object]:
    if parity_gaps is None:
        return {
            "ok": False,
            "required_gaps": ["retirement_parity_gaps_not_checked"],
        }
    gaps = _string_list(parity_gaps.get("required_gaps"))
    if parity_gaps.get("ok") is not True and not gaps:
        gaps.append("retirement_parity_not_clean")
    return {
        "ok": not gaps,
        "required_gaps": [f"retirement_parity:{gap}" for gap in gaps],
        "summary": {
            "adopter": parity_gaps.get("adopter", ""),
            "pending_package_count": len(_object_list(parity_gaps.get("pending_packages"))),
        },
    }


def _shadow_checks(shadow: dict[str, object] | None) -> dict[str, object]:
    if shadow is None:
        return {
            "ok": False,
            "required_gaps": ["retirement_shadow_not_checked"],
        }
    gaps = _string_list(shadow.get("required_gaps"))
    false_negative_count = _int_value(shadow.get("false_negative_count"))
    if shadow.get("ok") is not True and not gaps:
        gaps.append("retirement_shadow_not_matched")
    if false_negative_count:
        gaps.append(f"retirement_shadow_false_negative_count:{false_negative_count}")
    return {
        "ok": not gaps,
        "required_gaps": [f"retirement_shadow:{gap}" for gap in gaps],
        "summary": {
            "state": shadow.get("state", ""),
            "false_negative_count": false_negative_count,
            "accepted_summary": shadow.get("accepted_summary", {}),
        },
    }


def _report_state(lifecycle_stage: str, gaps: list[str]) -> str:
    if any(gap.startswith("retirement_docs_topology:") for gap in gaps):
        return "docs_topology_open"
    if any(gap.startswith("retirement_rollback_window_") for gap in gaps):
        return "rollback_window_evidence_open"
    return lifecycle_stage


def _lifecycle_stage(
    *,
    external_state: str,
    embedded_state: str,
    parity_ok: bool,
    shadow_ok: bool,
) -> str:
    if not parity_ok:
        return "parity_open"
    if not shadow_ok:
        return "shadow_open"
    if external_state not in EXTERNAL_DEFAULT_STATES:
        return "external_not_default"
    if embedded_state not in EMBEDDED_FROZEN_STATES:
        return "embedded_not_frozen"
    if external_state not in RETIREMENT_READY_STATES:
        return "rollback_window"
    return "retirement_ready"


def _next_actions(adopter: str, repo: Path, product: Path, gaps: list[str]) -> list[str]:
    if not gaps:
        return ["record separate Retirement Decision before removing embedded backend"]

    actions: list[str] = []
    if _has_any_gap(
        gaps,
        "retirement_parity",
        "retirement_shadow",
        "retirement_lifecycle_incomplete:parity_open",
        "retirement_lifecycle_incomplete:shadow_open",
    ):
        actions.append(
            "ethos parity shadow --adopter "
            f"{adopter} --target {repo.as_posix()} --execute --write-evidence --json"
        )
    if any(gap.startswith("retirement_external_backend_not_default") for gap in gaps):
        actions.append("switch adopter default backend to external under a reversible control")
    if any(gap.startswith("retirement_embedded_backend_not_frozen") for gap in gaps):
        actions.append("freeze embedded backend as fallback/reference during rollback window")
    if any(gap.startswith("retirement_docs_topology:") for gap in gaps):
        actions.append(f"ethos quality docs-topology --root {repo.as_posix()} --json")
    if any(gap.startswith("retirement_rollback_window_") for gap in gaps):
        actions.append(
            "populate [rollback_window] with a manifest and completed proof_report, "
            "work_lane_closeout, domain_gate, and assistant_playbook scenarios"
        )
    if any(gap.startswith("retirement_lifecycle_incomplete:rollback_window") for gap in gaps):
        actions.append(
            "record rollback-window evidence for proof/report, Work Lane, domain gate, "
            "and playbook paths"
        )
    actions.append(
        f"ethos fleet retirement-readiness --target {repo.as_posix()} "
        f"--root {product.as_posix()} --json"
    )
    return list(dict.fromkeys(actions))


def _has_any_gap(gaps: list[str], *prefixes: str) -> bool:
    return any(gap.startswith(prefix) for gap in gaps for prefix in prefixes)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _object_list(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return cast("list[object]", value)


def _int_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _repo_relative_path(repo: Path, path: str) -> Path | None:
    if not path or path.startswith(("/", "~")):
        return None
    resolved = (repo / path).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        return None
    return resolved


def _git_tracked(repo: Path, path: str) -> bool:
    if _repo_relative_path(repo, path) is None:
        return False
    result = subprocess.run(
        ["git", "-C", repo.as_posix(), "ls-files", "--error-unmatch", "--", path],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _git_commit_reachable(repo: Path, commit: str) -> bool:
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
