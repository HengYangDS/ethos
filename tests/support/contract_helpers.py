"""Shared fixtures for the CLI contract test suites.

The contract coverage lives across sibling `test_contracts*.py` modules split by
command family; these helpers (git plumbing, sample-repo scaffolding, adopt/proof
seeding) are the cross-cutting setup every split imports.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LaneLease
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path


class WorkLaneFixture(NamedTuple):
    """A generic adopted repository with its candidate and owned Work Lane."""

    repository: Path
    candidate: Path
    source: Path
    worktree: Path


def start_adopted_candidate(tmp_path: Path) -> tuple[Path, Path]:
    """Create an adopted accepted root and its candidate worktree."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    commit_openspec_baseline(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    return repo, candidate


def start_adopted_work_lane(
    tmp_path: Path,
    *,
    name: str = "feature",
    holder_ref: str = "agent:test:case:agent-test",
) -> WorkLaneFixture:
    """Create a generic adopted repository, candidate worktree, and owned lane."""
    repo, candidate = start_adopted_candidate(tmp_path)
    source = create_change_source_lane(
        repo,
        tmp_path / f"repo-work-source-{name}",
        branch=f"work/source-{name}",
        holder_ref=holder_ref,
    )
    worktree = tmp_path / f"repo-work-{name}"
    run_ethos(
        "lane",
        "start",
        name,
        "--root",
        repo.as_posix(),
        "--path",
        worktree.as_posix(),
        "--source-root",
        source.as_posix(),
        "--holder-ref",
        holder_ref,
        "--apply",
        "--json",
        cwd=repo,
    )
    return WorkLaneFixture(repo, candidate, source, worktree)


def lane_start_arguments(
    repository: Path,
    worktree: Path,
    *,
    source_root: Path | None = None,
    name: str = "feature",
    holder_ref: str = "agent:test:case:agent-test",
) -> tuple[str, ...]:
    """Build canonical CLI arguments for an applied test Work Lane start."""
    commit_openspec_baseline(repository)
    source_root = source_root or create_change_source_lane(
        repository,
        repository.parent / f"{repository.name}-work-source-{name}",
        branch=f"{load_branch_role_policy(repository).work_branch_prefix}source-{name}",
        holder_ref=holder_ref,
    )
    return (
        "lane",
        "start",
        name,
        "--root",
        repository.as_posix(),
        "--path",
        worktree.as_posix(),
        "--source-root",
        source_root.as_posix(),
        "--holder-ref",
        holder_ref,
        "--apply",
        "--json",
    )


def commit_fixture_file(root: Path, relative: str, content: str, message: str) -> str:
    """Write and commit a fixture file, returning the resulting HEAD."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    previous = git(root, "rev-parse", "HEAD")
    git(root, "add", relative)
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    head = git(root, "rev-parse", "HEAD")
    branch = git(root, "branch", "--show-current")
    holder = str(leases_by_branch(root).get(branch, {}).get("holder_ref") or "")
    if holder:
        original = os.environ.get("ETHOS_ACTOR")
        os.environ["ETHOS_ACTOR"] = holder
        try:
            report = work_lane_ref_transition_report(
                root=root,
                phase="committed",
                ref_name=f"refs/heads/{branch}",
                old_value=previous,
                new_value=head,
            )
        finally:
            if original is None:
                os.environ.pop("ETHOS_ACTOR", None)
            else:
                os.environ["ETHOS_ACTOR"] = original
        assert report["state"] == "lease_ref_advanced"
    return head


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def write_test_profile(root: Path, **updates: object) -> Path:
    """Write one strict profile fixture through the production declaration."""
    payload = RepositoryProfileDeclaration.bootstrap(root.resolve().name).model_dump(mode="python")
    payload.update(updates)
    profile = root / ".ethos" / "profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        render_repository_profile(RepositoryProfileDeclaration.model_validate(payload)),
        encoding="utf-8",
    )
    return profile


def init_git_repo(path: Path, *, object_format: str = "sha1") -> Path:
    path.mkdir(parents=True)
    git(path, "init", "--object-format=" + object_format, "-b", "dev")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.hooksPath", ".git/test-hooks")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def init_repo_with_candidate(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal accepted root and its linked candidate checkout."""
    repo = init_git_repo(tmp_path / "repo")
    adoption_plan(repo, apply=True)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "adopt ethos governance",
    )
    commit_openspec_baseline(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    return repo, candidate


def create_change_source_lane(
    repo: Path,
    path: Path,
    *,
    branch: str = "work/change-source",
    change_id: str = "fixture-change",
    scope: tuple[str, ...] = ("**",),
    holder_ref: str = "agent:test:case:source",
) -> Path:
    """Create one clean linked Work Lane carrying one active Change."""
    base_branch = load_branch_role_policy(repo).accepted_branch
    git(repo, "worktree", "add", "-b", branch, path.as_posix(), base_branch)
    _write_active_change_carrier(path, change_id=change_id, scope=scope)
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"declare {change_id}",
    )
    acquire_lease(
        repo / ".ethos" / "state" / "state.sqlite",
        lease=exact_lease(
            repo=repo,
            branch=branch,
            holder_ref=holder_ref,
            expected_head=git(path, "rev-parse", "HEAD"),
            carrier=f"openspec/changes/{change_id}/commitment.toml",
            change_id=change_id,
        ),
    )
    return path


def _lease_holder(root: Path, branch: str) -> str:
    holder = str(leases_by_branch(root).get(branch, {}).get("holder_ref") or "")
    assert holder
    return holder


def write_active_commitment(
    repo: Path,
    *,
    change_id: str = "fixture-change",
    scope: tuple[str, ...] = ("**",),
) -> None:
    """Write one complete-shape active OpenSpec Change for lifecycle fixtures."""
    _enable_openspec_profile(repo)
    repository_commitment = repo / ".ethos" / "commitment.toml"
    if not repository_commitment.exists():
        repository_id = f"repository:{repo.name}"
        repository_commitment.parent.mkdir(parents=True, exist_ok=True)
        repository_commitment.write_text(
            "\n".join(
                (
                    "schema_version = 1",
                    f'id = "{repository_id}"',
                    'intent = "Govern the fixture repository."',
                    f'subjects = ["{repository_id}"]',
                    "",
                )
            ),
            encoding="utf-8",
        )
    _write_openspec_baseline(repo)
    _write_active_change_carrier(repo, change_id=change_id, scope=scope)


def _write_openspec_baseline(repo: Path) -> None:
    """Write the accepted-repository OpenSpec config and capability specs."""
    openspec = repo / "openspec"
    specs = openspec / "specs" / "contracts"
    specs.mkdir(parents=True, exist_ok=True)
    (openspec / "config.yaml").write_text(
        "schema: spec-driven\n"
        "context: governed fixture repository\n"
        "rules:\n"
        "  proposal: [write intent]\n"
        "  specs: [write requirements]\n"
        "  tasks: [track work]\n"
        "  design: [record decisions]\n",
        encoding="utf-8",
    )
    (openspec / "specs" / "README.md").write_text("# Specs\n", encoding="utf-8")
    (specs / "spec.md").write_text(
        "## Purpose\n\n"
        "Exercise the governed fixture contract and its lifecycle semantics.\n\n"
        "## Requirements\n\n"
        "### Requirement: Governed fixture\n\n"
        "The governed fixture SHALL remain valid throughout its lifecycle.\n\n"
        "#### Scenario: Fixture is exercised\n\n"
        "- **WHEN** the test lifecycle runs\n"
        "- **THEN** the governed fixture remains valid\n",
        encoding="utf-8",
    )


def commit_openspec_baseline(repo: Path) -> None:
    """Commit the OpenSpec baseline before linked candidate/source worktrees."""
    _enable_openspec_profile(repo)
    _write_openspec_baseline(repo)
    if git(repo, "status", "--short", "--", "openspec", ".ethos/profile.toml"):
        git(repo, "add", "openspec/config.yaml", "openspec/specs", ".ethos/profile.toml")
        git(
            repo,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "seed OpenSpec baseline",
        )


def _write_active_change_carrier(
    repo: Path,
    *,
    change_id: str,
    scope: tuple[str, ...],
) -> None:
    """Write only one selected active OpenSpec Change carrier."""
    openspec = repo / "openspec"
    carrier = openspec / "changes" / change_id
    carrier.mkdir(parents=True, exist_ok=True)
    (carrier / "proposal.md").write_text(
        "## Why\n\nExercise the governed fixture lifecycle.\n\n"
        "## What Changes\n\n- Exercise one fixture change.\n\n"
        "## Capabilities\n\n"
        "- `contracts`: subject=fixture-contracts; reuse=extend; change=modify\n\n"
        "## Out Of Scope\n\n- Production behavior.\n",
        encoding="utf-8",
    )
    (carrier / "design.md").write_text(
        "## Context\n\nTest-only governed fixture.\n\n"
        "## Design\n\nUse the real OpenSpec carrier shape.\n\n"
        "## Alternatives\n\nNo compatibility fallback.\n\n"
        "## Proof Strategy\n\nRun focused lifecycle tests.\n",
        encoding="utf-8",
    )
    (carrier / "specs" / "contracts").mkdir(parents=True, exist_ok=True)
    (carrier / "specs" / "contracts" / "spec.md").write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Fixture change\n\n"
        "The fixture Commitment SHALL remain the single intent carrier.\n\n"
        "#### Scenario: Fixture change is selected\n\n"
        "- **WHEN** the fixture lifecycle selects the change\n"
        "- **THEN** its Commitment is the single intent carrier\n",
        encoding="utf-8",
    )
    (carrier / "commitment.toml").write_text(
        "schema_version = 1\n"
        f'id = "change:{change_id}"\n'
        'intent = "Exercise the governed fixture lifecycle."\n'
        'subjects = ["repository:self"]\n'
        f"scope = {list(scope)!r}\n".replace("'", '"')
        + 'permissions = ["git.ref.compare-and-swap"]\n',
        encoding="utf-8",
    )
    (carrier / "tasks.md").write_text("- [ ] Exercise fixture lifecycle\n", encoding="utf-8")


def commit_active_commitment(
    repo: Path,
    *,
    change_id: str = "fixture-change",
    scope: tuple[str, ...] = ("**",),
) -> str:
    """Commit one active fixture Commitment and return its canonical digest."""
    write_active_commitment(repo, change_id=change_id, scope=scope)
    if git(repo, "status", "--short"):
        git(repo, "add", ".")
        git(
            repo,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "declare active change",
        )
    head = git(repo, "rev-parse", "HEAD")
    return exact_commitment_fields(
        repo,
        head=head,
        carrier=f"openspec/changes/{change_id}/commitment.toml",
        change_id=change_id,
    )["base_commitment_digest"]


def _enable_openspec_profile(repo: Path) -> None:
    """Select the explicit OpenSpec profile adapter for lifecycle fixtures."""
    profile = repo / ".ethos" / "profile.toml"
    if not profile.exists():
        write_test_profile(repo)
    text = profile.read_text(encoding="utf-8")
    if "[openspec]" not in text:
        profile.write_text(
            text.rstrip() + '\n\n[openspec]\nmaterial_paths = ["openspec/**"]\n',
            encoding="utf-8",
        )


def write_role_policy(
    repo: Path,
    *,
    release_branch: str = "main",
    accepted_branch: str = "dev",
    candidate_branch: str = "stage/dev",
    work_branch_prefix: str = "lane/",
    proposal_branch_prefix: str = "review/",
    release_mirror: str = "independent",
) -> None:
    """Write and commit a branch-role policy fixture."""
    workspace_path = repo / ".ethos" / "workspace.toml"
    workspace_path.write_text(
        render_branch_policy(
            release_branch=release_branch,
            accepted_branch=accepted_branch,
            candidate_branch=candidate_branch,
            work_branch_prefix=work_branch_prefix,
            proposal_branch_prefix=proposal_branch_prefix,
            release_mirror=release_mirror,
        ),
        encoding="utf-8",
    )
    git(repo, "add", workspace_path.as_posix())
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "configure branch roles",
    )


def adopt_and_commit(repo: Path) -> None:
    plan = adoption_plan(repo, apply=True)
    assert plan["applied"] is True
    hook = repo / ".githooks" / "reference-transaction"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    (repo / ".ethos" / "workspace.toml").write_text(
        render_branch_policy(
            release_branch="main",
            accepted_branch="dev",
            candidate_branch="candidate/dev",
            work_branch_prefix="work/",
            proposal_branch_prefix="proposal/",
            release_mirror="independent",
        ),
        encoding="utf-8",
    )
    _declare_minimal_code_correctness(repo)
    _enable_openspec_profile(repo)
    write_publication_topology(repo)
    _write_openspec_baseline(repo)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "adopt ethos governance",
    )


def render_branch_policy(
    *,
    release_branch: str,
    accepted_branch: str,
    candidate_branch: str,
    work_branch_prefix: str,
    proposal_branch_prefix: str,
    release_mirror: str,
) -> str:
    """Render the complete branch-role policy shared by repository fixtures."""
    return "\n".join(
        (
            "[branch_roles]",
            f'release_branch = "{release_branch}"',
            f'accepted_branch = "{accepted_branch}"',
            f'candidate_branch = "{candidate_branch}"',
            f'work_branch_prefix = "{work_branch_prefix}"',
            f'proposal_branch_prefix = "{proposal_branch_prefix}"',
            f'release_mirror = "{release_mirror}"',
            "repository_family_worktrees = false",
            "",
        )
    )


def write_publication_topology(
    repo: Path, *, gitlab_remote: str = "origin", github_remote: str = "github"
) -> None:
    """Declare the canonical independent GitLab and GitHub test remotes."""
    release = repo / ".ethos" / "release.toml"
    release.parent.mkdir(parents=True, exist_ok=True)
    release.write_text(
        "\n".join(
            (
                "[publication]",
                f'gitlab_remote = "{gitlab_remote}"',
                f'github_remote = "{github_remote}"',
                "",
            )
        ),
        encoding="utf-8",
    )


def _declare_minimal_code_correctness(repo: Path) -> None:
    """Declare a minimal, axis-covering code-correctness map on the scaffolded profile.

    `ethos adopt` scaffolds a recognized adopter profile but deliberately leaves the
    code-correctness declaration commented out — an adopter's real test/lint commands are
    toolchain-specific and cannot be guessed. The honest onboarding lifecycle is therefore
    adopt -> DECLARE your native code-correctness gates -> prove. These fixtures walk that
    third step: they append two qualifying native gates (one behavior, one static-analysis)
    and map the required axes, so a proof seeded over the required floor is also complete
    on the code-correctness dimension (Tier 1.2)."""
    profile_path = repo / ".ethos" / "profile.toml"
    profile_path.write_text(
        profile_path.read_text(encoding="utf-8")
        + "\n"
        + "[proof]\n"
        + 'required_gates = ["sample-tests", "sample-static"]\n\n'
        + "[proof.code_axes]\n"
        + 'behavior = "sample-tests"\n'
        + 'static-analysis = "sample-static"\n\n'
        + "[[proof.gates]]\n"
        + 'id = "sample-tests"\n'
        + 'kind = "test"\n'
        + 'command = ["sample", "test"]\n'
        + 'dimensions = ["test", "coverage"]\n'
        + 'execution_mode = "subprocess"\n'
        + 'evidence_class = "proof"\n'
        + "trust_bearing = true\n"
        + 'tool_adapter = "repository-native"\n\n'
        + "[[proof.gates]]\n"
        + 'id = "sample-static"\n'
        + 'kind = "typing"\n'
        + 'command = ["sample", "typecheck"]\n'
        + 'dimensions = ["static-analysis"]\n'
        + 'execution_mode = "subprocess"\n'
        + 'evidence_class = "contract"\n'
        + "trust_bearing = true\n"
        + 'tool_adapter = "repository-native"\n',
        encoding="utf-8",
    )


def seed_executed_proof(repo: Path, head: str, *, full: bool = False) -> None:
    """Persist one complete policy-conformant generic proof Attestation."""
    branch = git(repo, "branch", "--show-current")
    holder = str(leases_by_branch(repo).get(branch, {}).get("holder_ref") or "")
    original = os.environ.get("ETHOS_ACTOR")
    if holder:
        os.environ["ETHOS_ACTOR"] = holder
    try:
        plan = proof_plan(
            repo,
            head=head,
            full=full,
            changed_paths=change_scope_paths_from_status(repo, workspace_status(repo)),
        )
        checks = tuple(
            conformant_proof_check(gate_id, repo, tree_ref=head)
            for gate_id in resolve_gate_policy(repo, tree_ref=head, full=full).gate_ids
        )
        attestation = issue_proof_attestation(
            repo,
            {
                "plan": plan,
                "checks": checks,
                "verdict": "pass",
                "issuer": "agent:test:fixture:proof",
                "issued_at": datetime.now(UTC),
                "scope": "repository",
                "boundary": "repository",
            },
        )
        persist_proof_attestation(repo, attestation)
    finally:
        if original is None:
            os.environ.pop("ETHOS_ACTOR", None)
        else:
            os.environ["ETHOS_ACTOR"] = original


def conformant_proof_check(gate_id: str, root: Path, *, tree_ref: str) -> dict[str, object]:
    """Build one terminal check result matching one committed gate policy identity."""
    gate = resolve_gate_policy(root, tree_ref=tree_ref, gate_ids=(gate_id,)).registry.get(gate_id)
    if gate is None:
        command: tuple[str, ...] = ("pytest",)
        trust_bearing = True
        evidence_class = "test"
    else:
        command = gate_execution_identity(gate)
        trust_bearing = gate.trust_bearing
        evidence_class = gate.evidence_class
    return {
        "action_id": gate_id,
        "command": list(command),
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "verdict": "pass",
        "evidence_class": evidence_class,
        "trust_bearing": trust_bearing,
        "diagnostics": [],
    }


def exact_lease(
    *,
    repo: Path,
    branch: str,
    holder_ref: str,
    expected_head: str,
    carrier: str,
    change_id: str | None = None,
    ttl_seconds: int = 86_400,
) -> LaneLease:
    now = datetime.now(UTC)
    binding = exact_commitment_fields(
        repo,
        head=expected_head,
        carrier=carrier,
        change_id=change_id,
    )
    return LaneLease(
        lane_incarnation_id=f"lane-incarnation:{uuid.uuid4()}",
        lease_id=f"lease:{uuid.uuid4()}",
        lane_ref=branch,
        holder_ref=holder_ref,
        epoch=1,
        issued_at=now,
        renewed_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        expected_head=binding["expected_head"],
        expected_tree=binding["expected_tree"],
        base_commitment_path=binding["base_commitment_path"],
        base_commitment_bytes_sha256=binding["base_commitment_bytes_sha256"],
        base_commitment_digest=binding["base_commitment_digest"],
        path_scope=(),
    )
