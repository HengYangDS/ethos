from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path

from ethos.repository.adoption.retirement.rollback import rollback_window_checks
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos.repository.policy.docs.topology import docs_topology_report
from ethos.repository.profile import load_repository_profile
from ethos_core.normalization.core import string_list
from ethos_core.normalization.core import string_mapping

RETIREMENT_READY_STATES = {"retirement_ready", "ready_to_retire", "retired"}
EXTERNAL_DEFAULT_STATES = RETIREMENT_READY_STATES | {"default", "rollback_window"}
EMBEDDED_FROZEN_STATES = {"frozen_fallback", "reference_only", "retired"}


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
        "backend_control": _backend_control_checks(repo, external_backend),
        "embedded_backend": _embedded_backend_checks(repo, embedded_backend),
        "rollback_window": rollback_window_checks(
            repo,
            product,
            rollback_window,
            context={
                "external_state": external_state,
                "embedded_state": embedded_state,
                "parity_ok": parity_ok,
                "shadow_ok": shadow_ok,
                "external_default_states": EXTERNAL_DEFAULT_STATES,
                "embedded_frozen_states": EMBEDDED_FROZEN_STATES,
            },
        ),
        "product_boundary": _product_boundary_checks(product, adoption_boundary),
        "docs_topology": _docs_topology_checks(repo),
        "generated_artifacts": _generated_artifacts_checks(repo),
        "parity": _parity_checks(parity_gaps),
        "shadow": _shadow_checks(shadow),
    }
    for check in checks.values():
        required_gaps.extend(string_list(check.get("required_gaps"), drop_empty=True))

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


def _backend_control_checks(repo: Path, external_backend: dict[str, Any]) -> dict[str, object]:
    control = str(external_backend.get("control") or "")
    expected_external_state = str(external_backend.get("state") or "")
    if not control:
        return {"ok": True, "path": "", "required_gaps": []}

    path_gap = _backend_control_path_gap(control)
    if path_gap:
        return {"ok": False, "path": control, "required_gaps": [path_gap]}

    path = repo / control
    if not path.exists():
        return {
            "ok": False,
            "path": path.as_posix(),
            "required_gaps": [f"retirement_backend_control_missing:{control}"],
        }

    data, parse_gap = _read_backend_control(path, control)
    if parse_gap:
        return {"ok": False, "path": path.as_posix(), "required_gaps": [parse_gap]}

    contract = _table(data, "contract")
    current = _table(data, "current")
    forbidden = _table(data, "forbidden")
    rollback = _table(data, "rollback_window")
    gaps = _backend_control_contract_gaps(contract)
    gaps.extend(_backend_control_current_gaps(current, expected_external_state))
    gaps.extend(_backend_control_forbidden_gaps(forbidden))
    gaps.extend(_backend_control_rollback_gaps(rollback, expected_external_state))

    return {
        "ok": not gaps,
        "path": path.as_posix(),
        "state": str(current.get("state") or ""),
        "default_backend": str(current.get("default_backend") or ""),
        "external_backend": str(current.get("external_backend") or ""),
        "rollback_mode": str(current.get("rollback_mode") or ""),
        "required_gaps": gaps,
    }


def _backend_control_path_gap(control: str) -> str:
    if control.startswith("/") or ".." in control.split("/"):
        return f"retirement_backend_control_path_outside_repo:{control}"
    return ""


def _read_backend_control(path: Path, control: str) -> tuple[dict[str, object], str]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), ""
    except (OSError, tomllib.TOMLDecodeError):
        return {}, f"retirement_backend_control_invalid:{control}"


def _table(data: dict[str, object], key: str) -> dict[str, object]:
    """Return one string-keyed table without leaking untyped TOML values."""
    return string_mapping(data.get(key))


def _backend_control_contract_gaps(contract: dict[str, object]) -> list[str]:
    gaps: list[str] = []
    asset_kind = str(contract.get("asset_kind") or "")
    profile_binding = str(contract.get("profile_binding") or "")
    if asset_kind != "ExternalEthosBackendSwitch":
        gaps.append(f"retirement_backend_control_asset_kind_invalid:{asset_kind or 'missing'}")
    if profile_binding and profile_binding != ".ethos/profile.toml":
        gaps.append(f"retirement_backend_control_profile_binding_invalid:{profile_binding}")
    return gaps


def _backend_control_current_gaps(
    current: dict[str, object], expected_external_state: str
) -> list[str]:
    gaps: list[str] = []
    control_state = str(current.get("state") or "")
    default_backend = str(current.get("default_backend") or "")
    external_backend_state = str(current.get("external_backend") or "")
    rollback_mode = str(current.get("rollback_mode") or "")

    if control_state != expected_external_state:
        gaps.append(
            "retirement_backend_control_state_mismatch:"
            f"{expected_external_state or 'missing'}:{control_state or 'missing'}"
        )

    expected_default = _expected_default_backend(expected_external_state)
    if default_backend != expected_default:
        gaps.append(
            "retirement_backend_control_default_mismatch:"
            f"{expected_default}:{default_backend or 'missing'}"
        )

    expected_external = _expected_control_external_backend(expected_external_state)
    if external_backend_state != expected_external:
        gaps.append(
            "retirement_backend_control_external_backend_mismatch:"
            f"{expected_external}:{external_backend_state or 'missing'}"
        )

    allowed_rollback_modes = {"embedded_fallback"}
    if expected_external_state == "retired" and control_state == "retired":
        allowed_rollback_modes.add("git_revert_or_restore_from_history")

    if rollback_mode not in allowed_rollback_modes:
        gaps.append(
            f"retirement_backend_control_rollback_mode_invalid:{rollback_mode or 'missing'}"
        )
    return gaps


def _backend_control_forbidden_gaps(forbidden: dict[str, object]) -> list[str]:
    gaps: list[str] = []
    for key in (
        "repo_local_execution_wrapper",
        "config_script_home",
        "adopter_named_external_product_root",
        "default_flip_without_rollback_window",
    ):
        if forbidden.get(key) is not True:
            gaps.append(f"retirement_backend_control_forbidden_not_true:{key}")
    return gaps


def _backend_control_rollback_gaps(
    rollback: dict[str, object], expected_external_state: str
) -> list[str]:
    default_or_later = expected_external_state in EXTERNAL_DEFAULT_STATES
    preview = expected_external_state == "adoption_preview"
    rollback_state = str(rollback.get("state") or "")
    if default_or_later and not preview and rollback_state not in {"planned", "active", "complete"}:
        return ["retirement_backend_control_rollback_window_not_declared"]
    return []


def _embedded_backend_checks(repo: Path, embedded_backend: dict[str, object]) -> dict[str, object]:
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


def _product_boundary_checks(
    product_root: Path, adoption_boundary: dict[str, object]
) -> dict[str, object]:
    forbidden = string_list(
        adoption_boundary.get("forbidden_external_product_roots"), drop_empty=True
    )
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
    gaps = [
        f"retirement_docs_topology:{gap}"
        for gap in string_list(report.get("required_gaps"), drop_empty=True)
    ]
    summary = string_mapping(report.get("summary"))
    return {
        "ok": not gaps,
        "state": report.get("state", ""),
        "missing_paths": string_list(report.get("missing_paths"), drop_empty=True),
        "forbidden_roots": string_list(report.get("forbidden_roots"), drop_empty=True),
        "time_state_roots": string_list(report.get("time_state_roots"), drop_empty=True),
        "profile_policy": report.get("profile_policy", {}),
        "required_gaps": gaps,
        "summary": {
            "required_path_count": summary.get("required_path_count", 0),
            "missing_required_path_count": summary.get("missing_required_path_count", 0),
        },
    }


def _generated_artifacts_checks(repo: Path) -> dict[str, object]:
    report = generated_artifact_topology_report(repo)
    gaps = [
        f"retirement_generated_artifacts:{gap}"
        for gap in string_list(report.get("required_gaps"), drop_empty=True)
    ]
    summary = string_mapping(report.get("summary"))
    return {
        "ok": not gaps,
        "state": report.get("state", ""),
        "allowed_paths": string_list(report.get("allowed_paths"), drop_empty=True),
        "denied_paths": string_list(report.get("denied_paths"), drop_empty=True),
        "review_paths": string_list(report.get("review_paths"), drop_empty=True),
        "required_gaps": gaps,
        "summary": {
            "allowed_path_count": summary.get("allowed_path_count", 0),
            "denied_path_count": summary.get("denied_path_count", 0),
            "review_path_count": summary.get("review_path_count", 0),
            "review_gap_count": summary.get("review_gap_count", 0),
        },
    }


def _parity_checks(parity_gaps: dict[str, object] | None) -> dict[str, object]:
    if parity_gaps is None:
        return {
            "ok": False,
            "required_gaps": ["retirement_parity_gaps_not_checked"],
        }
    gaps = string_list(parity_gaps.get("required_gaps"), drop_empty=True)
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
    gaps = string_list(shadow.get("required_gaps"), drop_empty=True)
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


def _expected_default_backend(external_state: str) -> str:
    if external_state in EXTERNAL_DEFAULT_STATES:
        return "external"
    return "embedded"


def _expected_control_external_backend(external_state: str) -> str:
    if external_state in RETIREMENT_READY_STATES:
        return "retirement_ready"
    if external_state in EXTERNAL_DEFAULT_STATES:
        return "default"
    return "preview"


def _report_state(lifecycle_stage: str, gaps: list[str]) -> str:
    if any(gap.startswith("retirement_docs_topology:") for gap in gaps):
        return "docs_topology_open"
    if any(gap.startswith("retirement_generated_artifacts:") for gap in gaps):
        return "generated_artifacts_open"
    if any(gap.startswith("retirement_backend_control_") for gap in gaps):
        return "backend_control_open"
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
    if any(gap.startswith("retirement_generated_artifacts:") for gap in gaps):
        actions.append(f"ethos quality generated-artifacts --root {repo.as_posix()} --json")
    if any(gap.startswith("retirement_backend_control_") for gap in gaps):
        actions.append("repair the profile-declared external-ethos-backend control manifest")
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
