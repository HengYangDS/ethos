"""Construct governed Git repositories for product contract tests."""

from __future__ import annotations

import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import NamedTuple

from ethos.adapters.store.state.lease.lifecycle.transitions import acquire_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.coordination import LaneLease
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.ethos_cli_runner import run_ethos
from tests.support.fixture_signer import configure_fixture_signer
from tests.support.paradigm import PARADIGM_OPENSPEC_CONFIG
from tests.support.runtime_scenarios import install_fixture_hook_runtime

PARADIGM_EDITORCONFIG = (
    "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\n"
)
PARADIGM_FORMATTERS = {
    ".config/checks/prettier/prettier.toml": 'printWidth = 100\nproseWrap = "preserve"\n',
    ".config/checks/taplo/taplo.toml": "[formatting]\ncolumn_width = 100\n",
    ".config/checks/ruff/ruff.toml": 'line-length = 100\ntarget-version = "py312"\n',
}
# A task-only mise owner exposes the common verbs and selects no native tools.
PARADIGM_TOOLCHAIN = {
    ".config/mise/config.toml": (
        '[settings]\nlocked = true\n\n[tasks]\nbootstrap = "uv sync --locked"\n'
        'check = "uv run nox -s check"\nfix = "uv run nox -s fix"\n'
    ),
    ".config/mise/mise.lock": "",
}


class WorkLaneFixture(NamedTuple):
    """A generic adopted repository with its candidate and owned Work Lane."""

    repository: Path
    candidate: Path
    worktree: Path


def start_adopted_candidate(
    tmp_path: Path, *, release_mirror: str = "independent", docs_only: bool = False
) -> tuple[Path, Path]:
    """Create an adopted accepted root and its candidate worktree.

    The generic fixture owns Git, profile, and OpenSpec facts. Package-runtime
    acceptance is orthogonal and must be requested explicitly by the tests that
    consume it; otherwise every semantic fixture would copy and hash a complete
    runtime image.
    """
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo, release_mirror=release_mirror, docs_only=docs_only)
    commit_openspec_baseline(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    install_fixture_hook_runtime(repo)
    return repo, candidate


def prepared_work_lane(
    tmp_path: Path,
    *,
    name: str = "feature",
    holder_ref: str = "agent:test:case:agent-test",
    release_mirror: str = "independent",
    docs_only: bool = False,
) -> WorkLaneFixture:
    """Prepare isolated native state; public start is exercised by its own acceptance."""
    repo, candidate = start_adopted_candidate(
        tmp_path, release_mirror=release_mirror, docs_only=docs_only
    )
    worktree = create_change_source_lane(
        repo,
        tmp_path / f"repo-work-{name}",
        branch=f"work/{name}",
        holder_ref=holder_ref,
        base_ref="candidate/dev",
    )
    return WorkLaneFixture(repo, candidate, worktree)


def lane_start_arguments(
    repository: Path,
    *,
    name: str = "feature",
    holder_ref: str = "agent:test:case:agent-test",
) -> tuple[str, ...]:
    """Build CLI arguments for an applied test Work Lane start at its dated sibling path."""
    commit_openspec_baseline(repository)
    return (
        "lane",
        "start",
        name,
        "--root",
        repository.as_posix(),
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
    git(root, "add", relative)
    empty_hooks = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "test-hooks"))
    empty_hooks.mkdir(parents=True, exist_ok=True)
    return _commit_fixture(root, message, hooks_path=empty_hooks)


def apply_accepted_closeout(repo: Path, accepted_before: str, candidate_head: str) -> None:
    """Apply and attest the exact candidate-to-accepted ref transition for a fixture."""
    policy = load_branch_role_policy(repo)
    accepted_root = repo.parent / f"{repo.name}-accepted"
    install_fixture_hook_runtime(repo)
    git(repo, "worktree", "add", accepted_root.as_posix(), policy.accepted_branch)
    run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_before,
        "--candidate-head",
        candidate_head,
        "--json",
        cwd=accepted_root,
    )


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
    configure_fixture_signer(path)
    git(path, "config", "core.hooksPath", ".git/test-hooks")
    (path / ".gitignore").write_text("", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (path / ".gitattributes").write_text("* text=auto eol=lf\n", encoding="utf-8")
    (path / ".editorconfig").write_text(PARADIGM_EDITORCONFIG, encoding="utf-8")
    for relative, content in PARADIGM_FORMATTERS.items():
        carrier = path / relative
        carrier.parent.mkdir(parents=True, exist_ok=True)
        carrier.write_text(content, encoding="utf-8")
    commit_fixture(path, "chore: initialize the fixture repository")
    return path


def init_repo_with_candidate(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal accepted root and its linked candidate checkout."""
    repo = init_git_repo(tmp_path / "repo")
    initialize_adopted_fixture(repo)
    commit_fixture(repo, "chore: adopt ethos governance")
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
    holder_ref: str = "agent:test:case:source",
    base_ref: str | None = None,
) -> Path:
    """Create isolated native lane state from the selected base and active Change."""
    base_branch = base_ref or load_branch_role_policy(repo).accepted_branch
    git(repo, "worktree", "add", "-b", branch, path.as_posix(), base_branch)
    _write_active_change_carrier(path, change_id=change_id)
    commit_fixture(path, f"docs(openspec): declare {change_id}")
    now = datetime.now(UTC)
    acquire_lease(
        state_database(repo),
        lease=LaneLease(
            lane_ref=branch,
            holder_ref=holder_ref,
            generation=1,
            expires_at=now + timedelta(days=1),
        ),
    )
    return path


def write_active_commitment(
    repo: Path,
    *,
    change_id: str = "fixture-change",
    scope: tuple[str, ...] = ("**",),
) -> None:
    """Write one complete official OpenSpec Change for lifecycle fixtures."""
    del scope
    _enable_openspec_profile(repo)
    _write_openspec_baseline(repo)
    _write_active_change_carrier(repo, change_id=change_id)


def _write_openspec_baseline(repo: Path) -> None:
    """Write the accepted-repository OpenSpec config and capability specs."""
    openspec = repo / "openspec"
    specs = openspec / "specs" / "contracts"
    specs.mkdir(parents=True, exist_ok=True)
    (openspec / "config.yaml").write_text(
        f"{PARADIGM_OPENSPEC_CONFIG}context: governed fixture repository\n", encoding="utf-8"
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
        _commit_fixture(repo, "docs(openspec): seed the baseline")


def _write_active_change_carrier(
    repo: Path,
    *,
    change_id: str,
) -> None:
    """Write one official OpenSpec Change without a parallel intent carrier."""
    openspec = repo / "openspec"
    carrier = openspec / "changes" / change_id
    carrier.mkdir(parents=True, exist_ok=True)
    (carrier / "proposal.md").write_text(
        "## Why\n\nExercise the governed fixture lifecycle.\n\n"
        "## What Changes\n\n- Exercise one fixture change.\n\n"
        "## Capabilities\n\n"
        "### New Capabilities\n\n- None.\n\n"
        "### Modified Capabilities\n\n"
        "- `contracts`: subject=fixture-contracts; reuse=extend; change=modify\n\n"
        "## Impact\n\n- Test fixtures only.\n\n"
        "## Out Of Scope\n\n- Production behavior.\n",
        encoding="utf-8",
    )
    (carrier / "design.md").write_text(
        "## Context\n\nTest-only governed fixture.\n\n"
        "## Goals / Non-Goals\n\nUse the real OpenSpec carrier shape.\n\n"
        "## Decisions\n\nNo compatibility fallback.\n\n"
        "## Risks / Trade-offs\n\nNone beyond the fixture.\n\n"
        "## Proof Strategy\n\nRun focused lifecycle tests.\n",
        encoding="utf-8",
    )
    (carrier / "specs" / "contracts").mkdir(parents=True, exist_ok=True)
    (carrier / "specs" / "contracts" / "spec.md").write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Fixture change\n\n"
        "The official OpenSpec Change SHALL remain the single intent carrier.\n\n"
        "#### Scenario: Fixture change is selected\n\n"
        "- **WHEN** the fixture lifecycle selects the change\n"
        "- **THEN** its official artifacts are the single intent carrier\n",
        encoding="utf-8",
    )
    (carrier / "tasks.md").write_text(
        "## 1. Fixture\n\n- [ ] 1.1 Exercise fixture lifecycle\n",
        encoding="utf-8",
    )


def commit_active_change(
    repo: Path,
    *,
    change_id: str = "fixture-change",
) -> str:
    """Commit one official active OpenSpec Change and return its exact HEAD."""
    write_active_commitment(repo, change_id=change_id)
    if git(repo, "status", "--short"):
        commit_fixture(repo, "docs(openspec): declare the active change")
    return git(repo, "rev-parse", "HEAD")


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


def write_role_policy(repo: Path, *, release_mirror: str = "independent") -> None:
    """Write and commit an explicit release mirror; the paradigm fixes the role names."""
    write_release_mirror(repo, release_mirror)
    commit_fixture(repo, "chore: configure the release mirror")


def write_release_mirror(repo: Path, release_mirror: str) -> None:
    """Set the release mirror in the release binding, keeping its other declarations."""
    release = repo / ".ethos" / "release.toml"
    release.parent.mkdir(parents=True, exist_ok=True)
    text = release.read_text(encoding="utf-8") if release.exists() else ""
    for declared in ("independent", "accepted_ff"):
        text = text.replace(render_release_mirror(declared), "")
    kept = text.rstrip("\n")
    rendered = render_release_mirror(release_mirror)
    release.write_text(f"{kept}\n\n{rendered}" if kept else rendered, encoding="utf-8")


def adopt_and_commit(
    repo: Path, *, release_mirror: str = "independent", docs_only: bool = False
) -> str:
    """Create code-free governance truth; quality tests opt into code subjects."""
    initialize_adopted_fixture(repo)
    declare_fixture_documentation_proof(repo)
    _enable_openspec_profile(repo)
    if not docs_only:
        write_publication_topology(
            repo,
            verification_command="git fsck --no-reflogs",
            installation_command="git --version",
            materialize_commands=False,
        )
    if release_mirror != "independent":
        write_release_mirror(repo, release_mirror)
    _write_openspec_baseline(repo)
    return commit_fixture(repo, "chore: adopt ethos governance")


def render_release_mirror(release_mirror: str) -> str:
    """Render the release binding's mirror for fixtures; the paradigm fixes the role names."""
    return f'[release]\nmirror = "{release_mirror}"\n'


def write_publication_topology(
    repo: Path,
    *,
    gitlab_remote: str = "gitlab",
    github_remote: str = "github",
    verification_command: str = "dev/verify",
    installation_command: str = "dev/install",
    gitlab_ci_surface: str = ".gitlab-ci.yml",
    github_ci_surface: str = ".github/workflows/verify.yml",
    materialize_commands: bool = True,
    host_provider: str = "",
) -> None:
    """Declare the canonical independent GitLab and GitHub test peers and optional host."""
    release = repo / ".ethos" / "release.toml"
    release.parent.mkdir(parents=True, exist_ok=True)
    if materialize_commands:
        for command in (verification_command, installation_command):
            path = repo / command
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(0o755)
    for surface in (gitlab_ci_surface, github_ci_surface):
        path = repo / surface
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# repository-native CI\n", encoding="utf-8")
    # The paradigm requires one pipeline model for the two Forges' pipeline files.
    model = repo / ".config/ci/pipeline.cue"
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_text("package ci\n", encoding="utf-8")
    host = ("[host_profile]", f'provider = "{host_provider}"', "") if host_provider else ()
    declared = tomllib.loads(release.read_text(encoding="utf-8")) if release.exists() else {}
    mirror = declared.get("release", {}).get("mirror")
    release.write_text(
        "\n".join(
            (
                *host,
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
                *((render_release_mirror(mirror),) if mirror else ()),
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
        '[[gates]]\nid = "publish"\nkind = "release"\n'
        'command = ["publish"]\ndepends_on = ["check"]\n\n'
        '[[gates]]\nid = "check"\nkind = "test"\n'
        'command = ["tools/check.sh"]\ndimensions = ["behavior"]\n'
        'evidence_class = "proof"\ntrust_bearing = true\n',
        encoding="utf-8",
    )
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "tools/check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")


def commit_fixture(root: Path, message: str, *, signed: bool = True) -> str:
    """Commit all fixture changes and return the resulting HEAD.

    Fixtures sign like every governed repository; a test that needs an unsigned
    source object, such as a signature repair, asks for one explicitly.
    """
    git(root, "add", ".")
    return _commit_fixture(root, message, signed=signed)


def committed_source_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """Commit a native-source fixture for public quality-gate tests."""
    repo = init_git_repo(tmp_path / "repo")
    for path, content in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    commit_fixture(repo, "chore: record native source")
    return repo


def _commit_fixture(
    root: Path, message: str, *, hooks_path: Path | None = None, signed: bool = True
) -> str:
    """Commit the staged fixture index with deterministic test identity."""
    hook_arguments = ("-c", f"core.hooksPath={hooks_path.as_posix()}") if hooks_path else ()
    git(
        root,
        *hook_arguments,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        *(() if signed else ("-c", "commit.gpgsign=false")),
        "commit",
        "-m",
        message,
    )
    return git(root, "rev-parse", "HEAD")


def initialize_adopted_fixture(root: Path) -> None:
    """Declare valid fixture state without retesting native onboarding in unrelated tests."""
    write_test_profile(root, openspec={"material_paths": ["**"]})
    config = root / "openspec/config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(PARADIGM_OPENSPEC_CONFIG, encoding="utf-8")
    write_paradigm_toolchain(root)


def write_paradigm_toolchain(root: Path) -> None:
    """Write the task-only mise owner that exposes the common verbs."""
    for relative, content in PARADIGM_TOOLCHAIN.items():
        carrier = root / relative
        carrier.parent.mkdir(parents=True, exist_ok=True)
        carrier.write_text(content, encoding="utf-8")


def declare_fixture_code_correctness(repo: Path) -> None:
    """Bind fixture-owned behavior and static checks without changing adopter defaults."""
    profile_path = repo / ".ethos" / "profile.toml"
    declaration = (
        "\n[proof]\n"
        'code_correctness_gates = ["sample-tests", "sample-static"]\n\n'
        "[proof.code_correctness_map]\n"
        'behavior = "sample-tests"\n'
        'static-analysis = "sample-static"\n\n'
    )
    for name, kind, command, dimensions, evidence in (
        ("sample-tests", "test", "test", '["test", "coverage"]', "proof"),
        ("sample-static", "typing", "typecheck", '["static-analysis"]', "contract"),
    ):
        declaration += (
            f'[[proof.gates]]\nid = "{name}"\nkind = "{kind}"\n'
            f'command = ["sample", "{command}"]\ndimensions = {dimensions}\n'
            f'execution_mode = "subprocess"\nevidence_class = "{evidence}"\n'
            'trust_bearing = true\ntool_adapter = "repository-native"\n\n'
        )
    profile_path.write_text(profile_path.read_text() + declaration.rstrip() + "\n")


def declare_fixture_documentation_proof(repo: Path, *, profile_id: str | None = None) -> None:
    """Check the committed OpenSpec baseline without inventing code subjects."""
    registry = repo / "system/gates.toml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        'schema_version = 1\nid = "fixture-docs-gates"\n'
        '[proof_sets]\ndefault = ["openspec-baseline"]\n'
        'full = ["openspec-baseline"]\n'
        '[[gates]]\nid = "openspec-baseline"\nkind = "governance"\n'
        'command = ["git", "grep", "-q", "^### Requirement:", "HEAD", "--", '
        '"openspec/specs"]\n'
        'asset_classes = ["markdown-docs"]\ndimensions = ["carrier-presence"]\n'
        'evidence_class = "contract"\ntrust_bearing = true\n'
        'tool_adapter = "git"\n',
        encoding="utf-8",
    )
    updates: dict[str, object] = {"proof": {"gate_registry": "system/gates.toml"}}
    if profile_id is not None:
        updates["profile_id"] = profile_id
    write_test_profile(repo, **updates)


def exact_lease(
    *,
    branch: str,
    holder_ref: str,
    ttl_seconds: int = 86_400,
) -> LaneLease:
    """Create one minimal exact Lease fixture."""
    now = datetime.now(UTC)
    return LaneLease(
        lane_ref=branch,
        holder_ref=holder_ref,
        generation=1,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
