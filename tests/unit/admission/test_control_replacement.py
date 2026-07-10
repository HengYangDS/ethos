from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.control_replacement import control_replacement_report
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_non_control_change_does_not_require_incumbent_verifier(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    (candidate / "README.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(candidate, "-c", "user.name=Test", "-c", "user.email=t@example.com", "commit", "-m", "docs")

    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=git(candidate, "rev-parse", "HEAD"),
    )

    assert report["required"] is False
    assert report["verdict"] == "allow"
    assert report["required_gaps"] == []


def test_control_change_defers_without_incumbent_or_external_bootstrap(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    path = candidate / "packages" / "ethos" / "src" / "ethos" / "adapters" / "admission"
    path.mkdir(parents=True)
    (path / "core.py").write_text("CONTROL = 'candidate'\n", encoding="utf-8")
    git(candidate, "add", ".")
    git(
        candidate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "control",
    )

    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=git(candidate, "rev-parse", "HEAD"),
    )

    assert report["required"] is True
    assert report["verdict"] == "defer"
    assert report["candidate_conformance"]["verifier_provenance"] == "candidate_runner"
    assert "incumbent_or_bootstrap_verifier_required" in report["required_gaps"]
    assert report["self_approval"] is False


def test_external_bootstrap_receipt_must_be_outside_candidate_and_exactly_bound(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    path = candidate / "system" / "gates.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("version = 2\n", encoding="utf-8")
    git(candidate, "add", ".")
    git(
        candidate, "-c", "user.name=Test", "-c", "user.email=t@example.com", "commit", "-m", "floor"
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    receipt = tmp_path / "bootstrap.json"
    receipt.write_text(
        (
            '{"kind":"control-replacement-verifier","provenance":"protected_external_bootstrap",'
            f'"accepted_head":"{accepted_head}","candidate_head":"{candidate_head}",'
            '"verdict":"allow","mints_authority":false}\n'
        ),
        encoding="utf-8",
    )

    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        external_receipt=receipt,
    )

    assert report["verdict"] == "allow"
    assert report["verifier_provenance"] == "protected_external_bootstrap"
    assert report["required_gaps"] == []


def test_external_evidence_and_declarative_policy_changes_require_incumbent_verifier(
    tmp_path: Path,
) -> None:
    for relative_path in (
        "packages/ethos-core/src/ethos_core/contracts/external_evidence.py",
        "system/evidence_boundaries.toml",
        "system/policies/generated-artifact-topology.toml",
        "system/workflows.toml",
    ):
        repo = init_git_repo(tmp_path / relative_path.replace("/", "-"))
        candidate = repo.with_name(f"{repo.name}-candidate-dev")
        git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
        path = candidate / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("candidate control\n", encoding="utf-8")
        git(candidate, "add", ".")
        git(
            candidate,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-m",
            "control",
        )

        report = control_replacement_report(
            accepted_root=repo,
            candidate_root=candidate,
            accepted_head=git(repo, "rev-parse", "HEAD"),
            candidate_head=git(candidate, "rev-parse", "HEAD"),
        )

        assert report["required"] is True, relative_path
