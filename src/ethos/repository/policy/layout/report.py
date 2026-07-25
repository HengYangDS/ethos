from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.layout.facades import dynamic_compat_facade_findings
from ethos.repository.policy.layout.facades import module_facade_findings
from ethos.repository.policy.layout.facades import package_init_facade_findings
from ethos.repository.policy.layout.facades import private_alias_findings
from ethos.repository.policy.layout.growth import flat_growth_findings
from ethos.repository.policy.layout.imports import package_root_submodule_import_findings
from ethos.repository.policy.layout.imports import private_from_import_regression_findings
from ethos.repository.policy.layout.naming import ambiguous_module_findings
from ethos.repository.policy.layout.naming import flat_directory_findings
from ethos.repository.policy.layout.naming import multiple_command_owner_findings
from ethos.repository.policy.layout.naming import suffix_group_findings
from ethos.repository.policy.layout.naming import suffix_module_findings
from ethos.repository.policy.layout.naming import surface_core_command_findings
from ethos.repository.policy.layout.policy import DEFAULT_FLAT_DIRECTORY_LIMIT
from ethos.repository.policy.layout.policy import DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT
from ethos.repository.policy.layout.policy import DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT
from ethos.repository.policy.layout.policy import DEFAULT_SUFFIX_GROUP_MIN
from ethos.repository.policy.layout.policy import POLICY_PATH
from ethos.repository.policy.layout.policy import load_policy
from ethos.repository.policy.layout.ratchet import baseline_gap_set
from ethos.repository.policy.layout.ratchet import baseline_growth_findings
from ethos.repository.policy.layout.ratchet import baseline_kind_counts
from ethos.repository.policy.layout.ratchet import baseline_kind_limit_findings
from ethos.repository.policy.layout.ratchet import baseline_kind_limits
from ethos.repository.policy.layout.ratchet import baseline_limit
from ethos.repository.policy.layout.ratchet import baseline_limit_gaps
from ethos.repository.policy.layout.ratchet import stale_baseline_findings

if TYPE_CHECKING:
    from pathlib import Path


DEBT_SUMMARY_KEYS = (
    "suffix_module_count",
    "suffix_flat_count",
    "flat_directory_count",
    "private_alias_count",
    "package_init_facade_count",
    "module_facade_count",
    "package_root_submodule_import_count",
    "dynamic_compat_facade_count",
    "private_from_import_regression_count",
)


def module_layout_report(root: Path) -> dict[str, object]:
    """Report module-layout violations enforced from `rules/module_layout.md`."""
    policy = load_policy(root)
    suffix_modules = suffix_module_findings(root, policy)
    suffix_groups = suffix_group_findings(root, policy)
    flat_directories = flat_directory_findings(root, policy)
    ambiguous_modules = ambiguous_module_findings(root, policy)
    surface_core_commands = surface_core_command_findings(root, policy)
    multiple_command_owners = multiple_command_owner_findings(root, policy)
    private_aliases = private_alias_findings(root, policy)
    package_init_facades = package_init_facade_findings(root, policy)
    module_facades = module_facade_findings(root, policy)
    package_root_submodule_imports = package_root_submodule_import_findings(root, policy)
    dynamic_compat_facades = dynamic_compat_facade_findings(root, policy)
    private_from_import_regressions = private_from_import_regression_findings(root, policy)
    flat_growth = flat_growth_findings(root, policy)
    baseline = baseline_gap_set(policy)
    baseline_growth = baseline_growth_findings(root, policy, baseline)
    findings = [
        *suffix_modules,
        *suffix_groups,
        *flat_directories,
        *ambiguous_modules,
        *surface_core_commands,
        *multiple_command_owners,
        *private_aliases,
        *package_init_facades,
        *module_facades,
        *package_root_submodule_imports,
        *dynamic_compat_facades,
        *private_from_import_regressions,
        *flat_growth,
    ]
    current_gaps = {str(item["gap"]) for item in findings}
    stale_baselines = stale_baseline_findings(baseline, current_gaps)
    limit = baseline_limit(policy)
    kind_counts = baseline_kind_counts(policy)
    kind_limit_findings = baseline_kind_limit_findings(policy, kind_counts)
    gaps = [str(item["gap"]) for item in findings if item["gap"] not in baseline]
    gaps.extend(str(item["gap"]) for item in stale_baselines)
    gaps.extend(baseline_limit_gaps(len(baseline), limit))
    gaps.extend(str(item["gap"]) for item in kind_limit_findings)
    gaps.extend(str(item["gap"]) for item in baseline_growth)
    summary = {
        "suffix_module_count": len(suffix_modules),
        "suffix_flat_count": len(suffix_groups),
        "flat_directory_count": len(flat_directories),
        "ambiguous_module_count": len(ambiguous_modules),
        "surface_core_command_count": len(surface_core_commands),
        "multiple_command_owner_count": len(multiple_command_owners),
        "private_alias_count": len(private_aliases),
        "package_init_facade_count": len(package_init_facades),
        "module_facade_count": len(module_facades),
        "package_root_submodule_import_count": len(package_root_submodule_imports),
        "dynamic_compat_facade_count": len(dynamic_compat_facades),
        "private_from_import_regression_count": len(private_from_import_regressions),
        "flat_growth_count": len(flat_growth),
        "baseline_growth_count": len(baseline_growth),
    }
    debt_count = sum(int(summary[key]) for key in DEBT_SUMMARY_KEYS)
    baseline_kind_limit_map = baseline_kind_limits(policy)
    ratchet = {
        "state": "debt_tracked" if debt_count else "clear",
        "debt_count": debt_count,
        "debt_kinds": [key for key in DEBT_SUMMARY_KEYS if int(summary[key]) > 0],
        "baseline_gap_count": len(baseline),
        "baseline_limit": limit,
        "baseline_kind_counts": kind_counts,
        "baseline_kind_limits": baseline_kind_limit_map,
        "next_action": (
            "shrink .config/checks/module-layout/policy.toml baselines when semantic "
            "subpackages remove debt; do not add compatibility facades or suffix-flat modules"
            if debt_count
            else "keep module-layout debt at zero"
        ),
    }
    summary["debt_count"] = debt_count

    return {
        "ok": not gaps,
        "state": "clean" if not gaps else "blocked",
        "policy": POLICY_PATH.as_posix(),
        "flat_directory_limit": int(
            policy.get("flat_directory_limit", DEFAULT_FLAT_DIRECTORY_LIMIT)
        ),
        "suffix_flat_group_min": int(policy.get("suffix_flat_group_min", DEFAULT_SUFFIX_GROUP_MIN)),
        "flat_growth_existing_module_limit": int(
            policy.get(
                "flat_growth_existing_module_limit",
                DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT,
            )
        ),
        "flat_growth_added_module_limit": int(
            policy.get(
                "flat_growth_added_module_limit",
                DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT,
            )
        ),
        "summary": summary,
        "ratchet": ratchet,
        "suffix_module_findings": suffix_modules,
        "suffix_flat_findings": suffix_groups,
        "flat_directory_findings": flat_directories,
        "ambiguous_module_findings": ambiguous_modules,
        "surface_core_command_findings": surface_core_commands,
        "multiple_command_owner_findings": multiple_command_owners,
        "private_alias_findings": private_aliases,
        "package_init_facade_findings": package_init_facades,
        "module_facade_findings": module_facades,
        "package_root_submodule_import_findings": package_root_submodule_imports,
        "dynamic_compat_facade_findings": dynamic_compat_facades,
        "private_from_import_regression_findings": private_from_import_regressions,
        "flat_growth_findings": flat_growth,
        "stale_baseline_findings": stale_baselines,
        "baseline_growth_findings": baseline_growth,
        "baseline_gap_count": len(baseline),
        "baseline_limit": limit,
        "baseline_kind_counts": kind_counts,
        "baseline_kind_limits": baseline_kind_limit_map,
        "baseline_kind_limit_findings": kind_limit_findings,
        "required_gaps": gaps,
    }
