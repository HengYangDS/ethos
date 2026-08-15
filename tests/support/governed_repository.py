"""Construct governed Git repositories for product contract tests."""

from __future__ import annotations

import hashlib
import os
import subprocess
import uuid
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import NamedTuple

import tomli_w

from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.proof import issue_proof_attestation
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import change_scope_paths_from_status
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LaneLease
from ethos.repository.adoption.planner import adoption_plan
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.ethos_cli_runner import run_ethos
from tests.support.semantic import commitment_v2


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
    install_hook_launchers(candidate)
    return repo, candidate


def start_adopted_work_lane(
    tmp_path: Path,
    *,
    name: str = "feature",
    holder_ref: str = "agent:test:case:agent-test",
    scope: tuple[str, ...] = ("**",),
) -> WorkLaneFixture:
    """Create a generic adopted repository, candidate worktree, and owned lane."""
    repo, candidate = start_adopted_candidate(tmp_path)
    source = create_change_source_lane(
        repo,
        tmp_path / f"repo-work-source-{name}",
        branch=f"work/source-{name}",
        holder_ref=holder_ref,
        scope=scope,
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
    empty_hooks = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "test-hooks"))
    empty_hooks.mkdir(parents=True, exist_ok=True)
    head = _commit_fixture(root, message, hooks_path=empty_hooks)
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
    """Run test Git plumbing without activating repository hook integration."""
    command = ["git", *args]
    if args[:1] != ("config",):
        command[1:1] = ["-c", "core.hooksPath=.git/test-hooks"]
    completed = subprocess.run(
        command,
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
    commit_fixture(path, "init")
    return path


def init_repo_with_candidate(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal accepted root and its linked candidate checkout."""
    repo = init_git_repo(tmp_path / "repo")
    adoption_plan(repo, apply=True)
    commit_fixture(repo, "adopt ethos governance")
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
    commit_fixture(path, f"declare {change_id}")
    acquire_lease(
        state_database(repo),
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
        repository_id = f"repository:fixture-{hashlib.sha256(repo.name.encode()).hexdigest()[:16]}"
        repository_commitment.parent.mkdir(parents=True, exist_ok=True)
        repository_commitment.write_text(
            tomli_w.dumps(
                commitment_v2(
                    id=repository_id,
                    intent="Govern the fixture repository.",
                    subjects=(repository_id,),
                ).model_dump(mode="python")
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
        _commit_fixture(repo, "seed OpenSpec baseline")


def _write_active_change_carrier(
    repo: Path,
    *,
    change_id: str,
    scope: tuple[str, ...],
) -> None:
    """Write only one selected active OpenSpec Change carrier."""
    openspec = repo / "openspec"
    repository_id = load_repository_commitment(repo).id
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
        "## Proof Strategy\n\nRun focused lifecycle tests.\n\n"
        "## Requirement To Task To Proof\n\n"
        "| Requirement | Task | Proof |\n"
        "| --- | --- | --- |\n"
        "| `contracts:Fixture change` | `1.1` | `unit-contracts` |\n",
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
        tomli_w.dumps(
            commitment_v2(
                id=f"change:{change_id}",
                intent="Exercise the governed fixture lifecycle.",
                subjects=(repository_id,),
                scope=scope,
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )
    (carrier / "tasks.md").write_text(
        "## 1. Fixture\n\n- [ ] 1.1 Exercise fixture lifecycle\n",
        encoding="utf-8",
    )


def commit_active_commitment(
    repo: Path,
    *,
    change_id: str = "fixture-change",
    scope: tuple[str, ...] = ("**",),
) -> str:
    """Commit one active fixture Commitment and return its canonical digest."""
    write_active_commitment(repo, change_id=change_id, scope=scope)
    if git(repo, "status", "--short"):
        commit_fixture(repo, "declare active change")
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
    commit_fixture(repo, "configure branch roles")


def adopt_and_commit(repo: Path) -> None:
    plan = adoption_plan(repo, apply=True)
    assert plan["applied"] is True
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
    commit_fixture(repo, "adopt ethos governance")


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
            "canonical_sibling_worktrees = false",
            "",
        )
    )


def write_publication_topology(
    repo: Path,
    *,
    gitlab_remote: str = "origin",
    github_remote: str = "github",
    verification_command: str = "dev/verify",
    installation_command: str = "dev/install",
    gitlab_ci_surface: str = ".gitlab-ci.yml",
    github_ci_surface: str = ".github/workflows/verify.yml",
) -> None:
    """Declare the canonical independent GitLab and GitHub test peers."""
    release = repo / ".ethos" / "release.toml"
    release.parent.mkdir(parents=True, exist_ok=True)
    for command in (verification_command, installation_command):
        path = repo / command
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    for surface in (gitlab_ci_surface, github_ci_surface):
        path = repo / surface
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# repository-native CI\n", encoding="utf-8")
    release.write_text(
        "\n".join(
            (
                "[publication]",
                f'local_verification_command = "{verification_command}"',
                f'local_installation_command = "{installation_command}"',
                "",
                "[[publication.peers]]",
                'id = "gitlab"',
                'provider = "gitlab"',
                'role = "organization_collaboration"',
                f'git_remote = "{gitlab_remote}"',
                'capabilities = ["repository", "ci_cd", "publication"]',
                f'ci_surface = "{gitlab_ci_surface}"',
                "",
                "[[publication.peers]]",
                'id = "github"',
                'provider = "github"',
                'role = "public_distribution"',
                f'git_remote = "{github_remote}"',
                'capabilities = ["repository", "ci_cd", "publication"]',
                f'ci_surface = "{github_ci_surface}"',
                "",
            )
        ),
        encoding="utf-8",
    )


def write_script_gate_policy(root: Path, *, full: bool = False) -> None:
    """Declare one script-backed proof policy for repository fixtures."""
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text(
        'profile_id = "policy-test"\n\n[proof]\ngate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )
    registry = root / "system/gates.toml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    default = '"check"' if full else '"publish"'
    registry.write_text(
        'schema_version = 1\nid = "policy-test"\n\n'
        f"[proof_sets]\ndefault = [{default}]\n"
        'full = ["check", "publish"]\n\n'
        '[[gates]]\nid = "publish"\nregistries = ["runtime"]\nkind = "release"\n'
        'command = ["publish"]\ndepends_on = ["check"]\n\n'
        '[[gates]]\nid = "check"\nregistries = ["runtime"]\nkind = "test"\n'
        'command = ["tools/check.sh"]\ndimensions = ["behavior"]\n'
        'evidence_class = "proof"\ntrust_bearing = true\n',
        encoding="utf-8",
    )
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "tools/check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def commit_fixture(root: Path, message: str) -> str:
    """Commit all fixture changes and return the resulting HEAD."""
    git(root, "add", ".")
    return _commit_fixture(root, message)


def _commit_fixture(root: Path, message: str, *, hooks_path: Path | None = None) -> str:
    """Commit the staged fixture index with deterministic test identity."""
    hook_arguments = ("-c", f"core.hooksPath={hooks_path.as_posix()}") if hooks_path else ()
    git(
        root,
        *hook_arguments,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


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
        + 'code_correctness_gates = ["sample-tests", "sample-static"]\n\n'
        + "[proof.code_correctness_map]\n"
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


def issue_conformant_proof(
    repo,
    head,
    *,
    plan=None,
    checks=None,
    issuer="agent:test:fixture:proof",
    issued_at=datetime(2026, 7, 26, tzinfo=UTC),
    boundary="repository",
):
    """Issue one proof Attestation from the repository's exact declared policy."""
    plan = plan or proof_plan(repo, head=head)
    if checks is None:
        checks = tuple(conformant_proof_check(node.id, repo, tree_ref=head) for node in plan.nodes)
    return issue_proof_attestation(
        repo,
        {
            "plan": plan,
            "checks": checks,
            "verdict": "pass",
            "issuer": issuer,
            "issued_at": issued_at,
            "scope": "repository",
            "boundary": boundary,
        },
    )


def seed_executed_proof(repo: Path, head: str, *, full: bool = False) -> None:
    """Persist one complete policy-conformant generic proof Attestation."""
    branch = git(repo, "branch", "--show-current")
    holder = str(leases_by_branch(repo).get(branch, {}).get("holder_ref") or "")
    original = os.environ.get("ETHOS_ACTOR")
    hooks_path = git(repo, "config", "--get", "core.hooksPath")
    installed_hooks = Path(hooks_path).name == "ethos-hooks"
    if holder:
        os.environ["ETHOS_ACTOR"] = holder
    if installed_hooks:
        git(repo, "config", "--worktree", "core.hooksPath", ".git/test-hooks")
    try:
        plan = proof_plan(
            repo,
            head=head,
            full=full,
            changed_paths=change_scope_paths_from_status(repo, workspace_status(repo)),
        )
        persist_proof_attestation(
            repo,
            issue_conformant_proof(repo, head, plan=plan, issued_at=datetime.now(UTC)),
        )
    finally:
        if installed_hooks:
            git(repo, "config", "--worktree", "core.hooksPath", hooks_path)
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
