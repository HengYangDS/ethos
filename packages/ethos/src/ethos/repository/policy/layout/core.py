from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.layout.baseline.core import baseline_gap_set
from ethos.repository.policy.layout.baseline.core import baseline_growth_findings
from ethos.repository.policy.layout.baseline.core import baseline_limit
from ethos.repository.policy.layout.baseline.core import baseline_limit_gaps
from ethos.repository.policy.layout.baseline.core import stale_baseline_findings
from ethos.repository.policy.layout.facade.core import module_facade_findings
from ethos.repository.policy.layout.facade.core import package_init_facade_findings
from ethos.repository.policy.layout.facade.core import private_alias_findings
from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_DIRECTORY_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT
from ethos.repository.policy.layout.filesystem.core import DEFAULT_SUFFIX_GROUP_MIN
from ethos.repository.policy.layout.filesystem.core import POLICY_PATH
from ethos.repository.policy.layout.filesystem.core import load_policy
from ethos.repository.policy.layout.growth.core import flat_growth_findings
from ethos.repository.policy.layout.imports.core import package_root_submodule_import_findings
from ethos.repository.policy.layout.naming.core import flat_directory_findings
from ethos.repository.policy.layout.naming.core import suffix_group_findings
from ethos.repository.policy.layout.naming.core import suffix_module_findings

if TYPE_CHECKING:
    from pathlib import Path


def module_layout_report(root: Path) -> dict[str, object]:
    """Report module-layout violations enforced from `rules/module_layout.md`."""
    policy = load_policy(root)
    suffix_modules = suffix_module_findings(root, policy)
    suffix_groups = suffix_group_findings(root, policy)
    flat_directories = flat_directory_findings(root, policy)
    private_aliases = private_alias_findings(root, policy)
    package_init_facades = package_init_facade_findings(root, policy)
    module_facades = module_facade_findings(root, policy)
    package_root_submodule_imports = package_root_submodule_import_findings(root, policy)
    flat_growth = flat_growth_findings(root, policy)
    baseline = baseline_gap_set(policy)
    baseline_growth = baseline_growth_findings(root, policy, baseline)
    findings = [
        *suffix_modules,
        *suffix_groups,
        *flat_directories,
        *private_aliases,
        *package_init_facades,
        *module_facades,
        *package_root_submodule_imports,
        *flat_growth,
    ]
    current_gaps = {str(item["gap"]) for item in findings}
    stale_baselines = stale_baseline_findings(baseline, current_gaps)
    limit = baseline_limit(policy)
    gaps = [str(item["gap"]) for item in findings if item["gap"] not in baseline]
    gaps.extend(str(item["gap"]) for item in stale_baselines)
    gaps.extend(baseline_limit_gaps(len(baseline), limit))
    gaps.extend(str(item["gap"]) for item in baseline_growth)
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
        "summary": {
            "suffix_module_count": len(suffix_modules),
            "suffix_flat_count": len(suffix_groups),
            "flat_directory_count": len(flat_directories),
            "private_alias_count": len(private_aliases),
            "package_init_facade_count": len(package_init_facades),
            "module_facade_count": len(module_facades),
            "package_root_submodule_import_count": len(package_root_submodule_imports),
            "flat_growth_count": len(flat_growth),
            "baseline_growth_count": len(baseline_growth),
        },
        "suffix_module_findings": suffix_modules,
        "suffix_flat_findings": suffix_groups,
        "flat_directory_findings": flat_directories,
        "private_alias_findings": private_aliases,
        "package_init_facade_findings": package_init_facades,
        "module_facade_findings": module_facades,
        "package_root_submodule_import_findings": package_root_submodule_imports,
        "flat_growth_findings": flat_growth,
        "stale_baseline_findings": stale_baselines,
        "baseline_growth_findings": baseline_growth,
        "baseline_gap_count": len(baseline),
        "baseline_limit": limit,
        "required_gaps": gaps,
    }
