"""End-to-end armed-hook proof that the candidate train survives WITHOUT the removed
`ETHOS_ALLOW_REF_MOVE` env bypass (slice 2c).

These tests install the REAL `.githooks/reference-transaction` script into a scratch repo
via `core.hooksPath`, with no bypass env set, and drive the sanctioned flow through the
actual `ethos` binary the hook shells out to. They are the load-bearing evidence that
removing the bypass did not brick the sanctioned path:

  * a sanctioned `land` + `closeout` advances candidate then dev through the armed hook;
  * a raw `git update-ref` to the same proven candidate head — carrying no one-shot
    closeout-intent marker — is BLOCKED (the bypass is gone, so nothing short-circuits the
    reducer); and the sanctioned closeout of that exact head still succeeds;
  * a candidate refresh-from-accepted rewind is admitted without a fresh proof (its target
    is already accepted-contained).

The committed-tree policy digest (which lets a gate-script-changing closeout validate even
though the hook fires while the accepted worktree still holds the old tree) is proven as a
focused unit in test_gate_policy_digest.py; here we exercise the whole ref-move path.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ethos.adapters.mutation.core import apply_candidate_to_accepted
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.lane_lifecycle.refresh import (
    refresh_candidate_from_accepted,
)
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import promotion_required_gate_ids
from tests.support.contract_helpers import _declare_minimal_code_correctness
from tests.support.contract_helpers import conformant_proof_run

_HOOK_SRC = Path(__file__).resolve().parents[3] / ".githooks" / "reference-transaction"
_RUNTIME_BOOTSTRAP_SRC = (
    Path(__file__).resolve().parents[3] / "tools" / "ci" / "scripts" / "with-python-runtime.sh"
)
_TEST_PYTHON = Path(os.environ.get("ETHOS_TEST_PYTHON", os.sys.executable)).absolute()
_TEST_VENV = _TEST_PYTHON.parent.parent


def _g(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def _lease_db(repo: Path) -> Path:
    """The accepted-root control-state DB the reference-transaction hook reads leases from."""
    return repo / ".ethos" / "state" / "state.sqlite"


def _commit(root: Path, message: str) -> str:
    _g(root, "-c", "user.name=t", "-c", "user.email=t@e.x", "commit", "-m", message)
    return _g(root, "rev-parse", "HEAD").stdout.strip()


def _seed_proof(root: Path, head: str) -> None:
    runs = tuple(
        conformant_proof_run(gate_id, root) for gate_id in promotion_required_gate_ids(root)
    )
    record_executed_proof(root, EvidenceSet.from_runs(id="p", head=head, runs=runs).to_dict())


def _armed_repo(tmp_path: Path, *, mirror: bool = False, adopter_profile: bool = False) -> Path:
    """A scratch candidate-train repo with the REAL reference-transaction hook armed and NO
    ETHOS_ALLOW_REF_MOVE in the environment.

    The installed hook resolves its interpreter from the scratch checkout's semantic
    ``build/runtime/venv`` home.  The fixture exposes a test interpreter there and
    symlinks package source so the scratch repo drives the real CLI without depending
    on the removed root ``.venv`` fallback.
    """
    src_root = Path(__file__).resolve().parents[3]
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "packages").mkdir()
    runtime_home = repo / "build" / "runtime" / "venv"
    runtime_home.parent.mkdir(parents=True)
    # `with-python-runtime.sh` deliberately calls `mkdir -p` on its semantic
    # environment home.  Symlinking the directory itself therefore breaks the
    # bootstrap; expose only its interpreter entrypoint instead.
    runtime_home.mkdir()
    for name in ("bin", "lib", "include"):
        source = _TEST_VENV / name
        if source.exists():
            (runtime_home / name).symlink_to(source, target_is_directory=True)
    (runtime_home / "pyvenv.cfg").symlink_to(_TEST_VENV / "pyvenv.cfg")
    (repo / "packages" / "ethos").symlink_to(src_root / "packages" / "ethos")
    (repo / "packages" / "ethos-core").symlink_to(src_root / "packages" / "ethos-core")
    _g(repo, "init", "-b", "dev")
    _g(repo, "config", "user.name", "t")
    _g(repo, "config", "user.email", "t@e.x")
    (repo / ".gitignore").write_text(".ethos/state/\nbuild\npackages\n", encoding="utf-8")
    hooks = repo / ".githooks"
    hooks.mkdir()
    shutil.copy(_HOOK_SRC, hooks / "reference-transaction")
    (hooks / "reference-transaction").chmod(0o755)
    runtime_script_dir = repo / "tools" / "ci" / "scripts"
    runtime_script_dir.mkdir(parents=True)
    shutil.copy(_RUNTIME_BOOTSTRAP_SRC, runtime_script_dir / "with-python-runtime.sh")
    (runtime_script_dir / "with-python-runtime.sh").chmod(0o755)
    (repo / "README.md").write_text("# x\n", encoding="utf-8")
    if adopter_profile:
        profile = repo / ".ethos" / "profile.toml"
        profile.parent.mkdir(exist_ok=True)
        profile.write_text('profile_id = "armed-adopter"\n', encoding="utf-8")
        _declare_minimal_code_correctness(repo)
    if mirror:
        policy = repo / ".ethos" / "workspace.toml"
        policy.parent.mkdir(exist_ok=True)
        policy.write_text('[branch_roles]\nrelease_mirror = "accepted_ff"\n', encoding="utf-8")
    _g(repo, "add", ".")
    _commit(repo, "init")
    if mirror:
        _g(repo, "branch", "main")
    _g(repo, "config", "core.hooksPath", ".githooks")
    _g(repo, "config", "ethos.acceptedBranch", "dev")
    candidate = tmp_path / "cand"
    _g(repo, "worktree", "add", "-b", "candidate/dev", str(candidate), "dev")
    _seed_semantic_runtime(candidate, src_root)
    return repo


def _seed_semantic_runtime(root: Path, source_root: Path) -> None:
    """Expose a checkout-local semantic runtime without tracking test scaffolding."""
    packages = root / "packages"
    packages.mkdir()
    for package in ("ethos", "ethos-core"):
        shutil.copytree(
            source_root / "packages" / package,
            packages / package,
            ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__"),
        )
    _seed_core_declaration_resources(root, source_root)
    runtime_home = root / "build" / "runtime" / "venv"
    # A linked worktree may already inherit its ignored runtime directory from
    # the initial checkout. Recreate only this fixture-owned semantic venv so
    # the test remains independent of host checkout residue.
    if runtime_home.exists() or runtime_home.is_symlink():
        if runtime_home.is_dir() and not runtime_home.is_symlink():
            shutil.rmtree(runtime_home)
        else:
            runtime_home.unlink()
    runtime_home.parent.mkdir(parents=True, exist_ok=True)
    runtime_home.mkdir()
    for name in ("bin", "lib", "include"):
        source = _TEST_VENV / name
        if source.exists():
            (runtime_home / name).symlink_to(source, target_is_directory=True)
    (runtime_home / "pyvenv.cfg").symlink_to(_TEST_VENV / "pyvenv.cfg")


def _seed_core_declaration_resources(root: Path, source_root: Path) -> None:
    """Materialize the core declarations that the candidate CLI loads at startup."""
    resource_root = root / "packages" / "ethos-core" / "src" / "ethos_core" / "data"
    resource_root.mkdir()
    for source, name in (
        (source_root / "system" / "commands.toml", "commands.toml"),
        (source_root / "system" / "gates.toml", "gates.toml"),
        (source_root / "system" / "invalid_states.toml", "invalid_states.toml"),
        (source_root / "system" / "workflows.toml", "workflows.toml"),
        (source_root / "system" / "coupling.toml", "coupling.toml"),
        (source_root / "system" / "standards.toml", "standards.toml"),
        (
            source_root / "system" / "policies" / "evidence-layout.toml",
            "evidence_layout.toml",
        ),
        (
            source_root / "system" / "policies" / "generated-artifact-topology.toml",
            "generated_artifact_topology.toml",
        ),
    ):
        shutil.copy2(source, resource_root / name)


def _materialize_accepted_ethos_package(repo: Path) -> Path:
    """Replace only accepted's ignored package symlink with a private source copy."""
    package = repo / "packages" / "ethos"
    source = package.resolve()
    package.unlink()
    shutil.copytree(source, package)
    return package


def _land_proven_work(
    repo: Path, tmp_path: Path, name: str, content: str, *, profile_mode: str = ""
) -> str:
    """Create a lease-backed work lane, commit + prove work, land it onto candidate.
    Returns the candidate head."""
    work = tmp_path / name
    # Bind the lease BEFORE creating the lane worktree: `git worktree add` re-asserts the
    # new branch ref with old==new during setup, which routes through the lease admission
    # (not the old==zero creation short-circuit). The lease must exist and its expected_head
    # must equal the branch's base (the candidate head the lane forks from) or the reassert
    # trips lease_head_stale.
    candidate_head = _g(repo, "rev-parse", "candidate/dev").stdout.strip()
    acquire_lease(
        _lease_db(repo),
        subject=f"work/{name}",
        holder_ref="agent:test:case:agent-test",
        payload={"expected_head": candidate_head},
    )
    _g(repo, "worktree", "add", "-b", f"work/{name}", str(work), "candidate/dev")
    (work / f"{name}.txt").write_text(content, encoding="utf-8")
    if profile_mode == "drop":
        (work / ".ethos" / "profile.toml").unlink()
    _g(work, "add", ".")
    work_head = _commit(work, f"work {name}")
    _seed_proof(work, work_head)
    landed = apply_land_to_candidate(root=work, authorized=True, expect_head=work_head)
    assert landed["ok"] is True, landed
    return work_head


def test_sanctioned_land_and_closeout_pass_through_armed_hook(tmp_path: Path) -> None:
    """With the bypass removed, sanctioned land + closeout still advance candidate then dev
    through the armed reference-transaction hook."""
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path, mirror=True, adopter_profile=True)

    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n", profile_mode="drop")
    assert _g(repo, "rev-parse", "candidate/dev").stdout.strip() == candidate_head

    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)
    assert closeout["ok"] is True, closeout
    assert closeout["state"] == "accepted_validated"
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head
    assert _g(repo, "rev-parse", "main").stdout.strip() == candidate_head


def test_raw_ref_move_to_proven_head_is_blocked_without_marker(tmp_path: Path) -> None:
    """A hand-typed `git update-ref dev <candidate_head>` — proof present but NO one-shot
    closeout-intent marker — is aborted by the armed hook, while the sanctioned closeout of
    the very same head succeeds. This is the discrimination the removed env bypass used to
    defeat."""
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path, mirror=True, adopter_profile=True)

    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n", profile_mode="drop")
    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    # Even with a valid proof pre-placed at the accepted root, a raw ref move carries no
    # closeout-intent marker for this transition, so the hook aborts it.
    _seed_proof(repo, candidate_head)
    raw = _g(repo, "update-ref", "refs/heads/dev", candidate_head, dev_before)
    assert raw.returncode != 0
    assert _g(repo, "rev-parse", "dev").stdout.strip() == dev_before
    raw_main = _g(repo, "update-ref", "refs/heads/main", candidate_head, dev_before)
    assert raw_main.returncode != 0

    # The sanctioned closeout of the identical head writes the marker and is admitted.
    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)
    assert closeout["ok"] is True, closeout
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head
    assert _g(repo, "rev-parse", "main").stdout.strip() == candidate_head


def test_candidate_refresh_from_accepted_admitted_without_bypass(
    tmp_path: Path,
) -> None:
    """`refresh_candidate_from_accepted` rewinds candidate onto the accepted head; the armed
    hook admits it without a fresh proof because the target is already accepted-contained.
    Without the refresh exemption this would self-block once the bypass is gone."""
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path)

    # Advance dev ahead of candidate by landing + closing out one change.
    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n")
    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)
    accepted_head = _g(repo, "rev-parse", "dev").stdout.strip()
    assert accepted_head == candidate_head

    # Move dev one commit further via a second sanctioned round so candidate lags accepted.
    second_head = _land_proven_work(repo, tmp_path, "w2", "yo\n")
    apply_candidate_to_accepted(
        root=repo,
        authorized=True,
        expect_head=_g(repo, "rev-parse", "dev").stdout.strip(),
    )
    accepted_head = _g(repo, "rev-parse", "dev").stdout.strip()
    assert accepted_head == second_head

    # Rewind candidate onto accepted — admitted through the armed hook, no proof required.
    refreshed = refresh_candidate_from_accepted(
        root=repo, apply=True, authorized=True, expect_head=accepted_head
    )
    assert refreshed["ok"] is True, refreshed
    assert _g(repo, "rev-parse", "candidate/dev").stdout.strip() == accepted_head


def test_closeout_binds_semantic_hook_runner_to_candidate_checkout(
    tmp_path: Path,
) -> None:
    """A candidate control change must not be judged by accepted-old source.

    The accepted hook shell is intentionally retained, but this regression makes its
    incumbent import graph deny every ref transaction after candidate has replaced the
    semantic hook reducer.  A sanctioned closeout must nevertheless succeed, because
    the candidate checkout at the promoted head is the only valid semantic runner.
    """
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path)
    candidate = tmp_path / "cand"

    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n")
    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    candidate_runtime = candidate / "build" / "runtime" / "venv" / "runtime-cache.txt"
    candidate_runtime.write_text("untracked runtime cache\n", encoding="utf-8")
    assert (candidate / "packages" / "ethos").is_dir()
    assert not (candidate / "packages" / "ethos").is_symlink()

    accepted_package = _materialize_accepted_ethos_package(repo)
    accepted_hook_core = accepted_package / "src" / "ethos" / "surface" / "cli" / "hook" / "core.py"
    accepted_hook_core.write_text("raise SystemExit(91)\n", encoding="utf-8")

    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)

    assert closeout["ok"] is True, closeout
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head
    assert candidate.resolve() != repo.resolve()
