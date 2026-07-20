from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.surface.cli.root.planning as planning_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.openspec.core import openspec_governance_report
from ethos.repository.adoption.planner import adoption_plan
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked

if TYPE_CHECKING:
    from pathlib import Path


def test_fresh_adopter_without_material_change_does_not_require_openspec_workspace(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    report = openspec_governance_report(repo, lifecycle=True, require_workspace=False)

    assert report["ok"] is True
    assert report["state"] == "not_applicable"
    assert report["required_gaps"] == []
    assert report["lifecycle"]["scope_binding"]["state"] == "no_material_paths"


def test_fresh_adopter_material_change_requires_openspec_workspace(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)

    report = openspec_governance_report(
        repo,
        lifecycle=True,
        changed_paths=("docs/governance/policy.md",),
        require_workspace=False,
    )

    assert report["ok"] is False
    assert {
        "openspec_config_missing",
        "openspec_directory_missing",
        "openspec_specs_missing",
        "openspec_material_path_uncovered:docs/governance/policy.md",
    } <= set(report["required_gaps"])
    assert report["lifecycle"]["scope_binding"]["state"] == "uncovered"


def test_valid_adopter_plan_and_prove_surface_lifecycle_gap(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt generic profile")
    gap = "openspec_claim_binding_missing:material-change"
    calls: list[tuple[Path, bool]] = []

    def report(root: Path, *, lifecycle: bool = False, **_kwargs: object) -> dict[str, object]:
        calls.append((root, lifecycle))
        return {"ok": False, "required_gaps": [gap]}

    monkeypatch.setattr(planning_cli, "openspec_governance_report", report)
    monkeypatch.setattr(proof_cli, "openspec_governance_report", report)
    plan = run_ethos("plan", "--root", repo.as_posix(), "--json")
    prove = run_ethos_blocked("prove", "--root", repo.as_posix(), "--json")

    assert plan["ok"] is False
    assert plan["required_gaps"] == [gap]
    assert prove["required_gaps"] == [
        gap,
        "adopter_profile_missing_code_correctness_gates",
    ]
    assert calls == [(repo, True), (repo, True)]
