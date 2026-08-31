from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.verdict import close_verdict
from ethos.repository.policy.layout.facades import dynamic_compat_facade_findings
from ethos.repository.policy.layout.facades import module_facade_findings
from ethos.repository.policy.layout.facades import package_init_facade_findings
from ethos.repository.policy.layout.facades import private_alias_findings
from ethos.repository.policy.layout.imports import package_root_submodule_import_findings
from ethos.repository.policy.layout.imports import private_from_import_findings
from ethos.repository.policy.layout.naming import ambiguous_module_findings
from ethos.repository.policy.layout.naming import ambiguous_package_findings
from ethos.repository.policy.layout.naming import multiple_command_owner_findings
from ethos.repository.policy.layout.policy import POLICY_PATH
from ethos.repository.policy.layout.policy import configured_package_paths
from ethos.repository.policy.layout.policy import configured_semantic_paths
from ethos.repository.policy.layout.policy import empty_package_findings
from ethos.repository.policy.layout.policy import load_policy

if TYPE_CHECKING:
    from pathlib import Path


def module_layout_report(
    root: Path,
    *,
    files: tuple[Path, ...] | None = None,
) -> dict[str, object]:
    """Report semantic-boundary violations across repository-owned Python."""
    policy = load_policy(root)
    finding_groups: dict[str, list[dict[str, object]]] = {
        "ambiguous_module_findings": ambiguous_module_findings(root, policy, files),
        "ambiguous_package_findings": ambiguous_package_findings(root, policy, files),
        "empty_package_findings": empty_package_findings(root, policy, files),
        "multiple_command_owner_findings": multiple_command_owner_findings(root, policy, files),
        "private_alias_findings": private_alias_findings(root, policy, files),
        "package_init_facade_findings": package_init_facade_findings(root, policy, files),
        "module_facade_findings": module_facade_findings(root, policy, files),
        "package_root_submodule_import_findings": package_root_submodule_import_findings(
            root, policy, files
        ),
        "dynamic_compat_facade_findings": dynamic_compat_facade_findings(root, policy, files),
        "private_from_import_findings": private_from_import_findings(root, policy, files),
    }
    gaps = [str(finding["gap"]) for findings in finding_groups.values() for finding in findings]
    summary = {
        key.removesuffix("_findings") + "_count": len(findings)
        for key, findings in finding_groups.items()
    }
    summary["gap_count"] = len(gaps)
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "state": "clean" if not gaps else "blocked",
        "policy": POLICY_PATH.as_posix(),
        "semantic_paths": configured_semantic_paths(policy),
        "package_paths": configured_package_paths(policy),
        "summary": summary,
        **finding_groups,
        "required_gaps": gaps,
    }
