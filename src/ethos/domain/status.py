"""Repository audit dispatch for product and adopter profiles."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.repository.audit as repository_audit_module
from ethos.adapters.openspec.governance import openspec_governance_report
from ethos.adapters.openspec.observation import openspec_shape_report
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.hook.binding import hook_runtime_binding
from ethos.repository.adoption.fleet import inspect_adopter
from ethos.repository.context import repository_context
from ethos.repository.profile import profile_gate_registry

if TYPE_CHECKING:
    from pathlib import Path


def audit_for_root(root: Path, *, openspec_mode: str = "shape") -> dict[str, object]:
    """Dispatch from the profile's declared audit capability."""
    if profile_gate_registry(root):
        reporter = openspec_governance_report if openspec_mode == "deep" else None
        write_admission_gaps = (
            [str(gap) for gap in hook_runtime_binding(root)["required_gaps"]]
            if (root / ".ethos/profile.toml").is_file()
            else []
        )
        return repository_audit_module.repository_audit(
            root,
            openspec_mode=openspec_mode,
            openspec_reporter=reporter,
            write_admission_gaps=write_admission_gaps,
            tracked_documents=tuple(git_files(root, "*.md")),
            openspec_shape=openspec_shape_report(root),
        )
    return adopter_audit(root)


def adopter_audit(root: Path) -> dict[str, object]:
    """Validate only the one adopter binding; capabilities remain explicit opt-ins."""
    adopter = inspect_adopter(root)
    gaps = list(cast("list[str]", adopter["required_gaps"]))
    capabilities = cast("dict[str, dict[str, bool]]", adopter["adopter"])["capabilities"]
    return {
        "verdict": "pass" if not gaps else "block",
        "mode": "repository",
        "governance_context": repository_context(root),
        "required_gaps": gaps,
        "adopter": adopter,
        "openspec": {
            "verdict": "pass",
            "mode": "adopter-shape",
            "configured": bool(capabilities["openspec"]),
            "required_gaps": [],
        },
    }
