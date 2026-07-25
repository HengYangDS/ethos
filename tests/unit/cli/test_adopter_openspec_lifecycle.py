from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.surface.cli.root.planning as planning_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.mutation.proof import proof_plan
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


def test_plan_surfaces_plan_ir_block_as_top_level_block(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    carrier = repo / "openspec" / "changes" / "foreign"
    carrier.mkdir(parents=True)
    (carrier / "contract.toml").write_text(
        'schema_version = 1\nid = "change:foreign"\nintent = "foreign"\n'
        'subjects = ["repository:foreign"]\nscope = ["**"]\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "foreign contract")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--json")

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "repository_subject_mismatch" in payload["required_gaps"]


def test_prove_does_not_run_nodes_from_a_blocked_plan(monkeypatch, tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "adopter")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt")
    blocked = proof_plan(repo, head=git(repo, "rev-parse", "HEAD")).model_copy(
        update={"validation_issues": ("blocked-plan",)}
    )

    monkeypatch.setattr(proof_cli, "proof_plan", lambda *_args, **_kwargs: blocked)
    monkeypatch.setattr(
        proof_cli.LocalSubprocessRunner,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runner called")),
    )

    payload = run_ethos_blocked(
        "prove",
        "--execute",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["required_gaps"] == ["blocked-plan"]


def test_adopt_cli_applies_the_reviewed_identity_and_plan(tmp_path: Path) -> None:
    target = init_git_repo(tmp_path / "adopter")
    reviewed = adoption_plan(target)

    payload = run_ethos(
        "adopt",
        "--apply",
        "--authorize",
        "--expect-head",
        git(target, "rev-parse", "HEAD"),
        "--repository-id",
        str(reviewed["repository_id"]),
        "--expect-plan-digest",
        str(reviewed["plan_digest"]),
        "--root",
        target.as_posix(),
        "--json",
    )

    assert payload["state"] == "applied"
    assert payload["data"]["repository_id"] == reviewed["repository_id"]
    assert payload["data"]["plan_digest"] == reviewed["plan_digest"]
