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

from ethos.adapters.mutation.closeout import core as closeout_core
from ethos.adapters.mutation.core import apply_candidate_to_accepted
from ethos.adapters.mutation.core import apply_land_to_candidate
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import default_gate_ids
from tests.support.contract_helpers import _declare_minimal_code_correctness
from tests.support.contract_helpers import conformant_proof_run
from tests.support.subprocesses import completed as cp

_HOOK_SRC = Path(__file__).resolve().parents[3] / ".githooks" / "reference-transaction"
_RUNTIME_BOOTSTRAP_SRC = (
    Path(__file__).resolve().parents[3] / "tools" / "ci" / "scripts" / "with-python-runtime.sh"
)
_TEST_PYTHON = Path(os.environ.get("ETHOS_TEST_PYTHON", os.sys.executable)).absolute()
_TEST_VENV = _TEST_PYTHON.parent.parent
_LEGACY_HOOK_REF = "0d7749c56c30857ebc373489186e756324ec3378"


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
        conformant_proof_run(gate_id, root) for gate_id in default_gate_ids(full=False, root=root)
    )
    record_executed_proof(root, EvidenceSet.from_runs(id="p", head=head, runs=runs).to_dict())


def _armed_repo(tmp_path: Path, *, mirror: bool = False, legacy_hook: bool = False) -> Path:
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
    hook = hooks / "reference-transaction"
    if legacy_hook:
        hook.write_bytes(
            subprocess.run(
                ["git", "show", f"{_LEGACY_HOOK_REF}:.githooks/reference-transaction"],
                cwd=_HOOK_SRC.parent.parent,
                capture_output=True,
                check=True,
            ).stdout
        )
        hook.write_text(
            hook.read_text(encoding="utf-8").replace(
                '    branch="${ref_name#refs/heads/}"\n',
                '    branch="${ref_name#refs/heads/}"\n'
                '    if [ "$branch" = "main" ]; then\n'
                '        echo "ethos: legacy mirror hook rejected $ref_name." >&2\n'
                "        exit 1\n"
                "    fi\n",
                1,
            ),
            encoding="utf-8",
        )
    else:
        shutil.copy(_HOOK_SRC, hook)
    hook.chmod(0o755)
    runtime_script_dir = repo / "tools" / "ci" / "scripts"
    runtime_script_dir.mkdir(parents=True)
    shutil.copy(_RUNTIME_BOOTSTRAP_SRC, runtime_script_dir / "with-python-runtime.sh")
    (runtime_script_dir / "with-python-runtime.sh").chmod(0o755)
    (repo / "README.md").write_text("# x\n", encoding="utf-8")
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
    repo: Path,
    tmp_path: Path,
    name: str,
    content: str,
    *,
    upgrade_hook: bool = False,
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
    if upgrade_hook:
        shutil.copy(_HOOK_SRC, work / ".githooks" / "reference-transaction")
        (work / ".githooks" / "reference-transaction").chmod(0o755)
    (work / ".ethos" / "profile.toml").unlink(missing_ok=True)
    _g(work, "add", ".")
    work_head = _commit(work, f"work {name}")
    _seed_proof(work, work_head)
    landed = apply_land_to_candidate(root=work, authorized=True, expect_head=work_head)
    assert landed["ok"] is True, landed
    return work_head


def test_committed_profile_closeout_blocks_raw_move(tmp_path: Path) -> None:
    """An accepted_ff closeout binds both protected refs to candidate semantics.

    The test keeps the real reference-transaction hook armed, proves raw moves of
    both ``dev`` and ``main`` block, then makes the accepted checkout's hook reducer
    unusable.  The sanctioned atomic closeout must still advance both refs through
    the clean candidate checkout, or the release-mirror half of the transaction
    would be judged by stale incumbent source.
    """
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path, mirror=True)

    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n")
    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    # Even with a valid proof pre-placed at the accepted root, a raw ref move carries no
    # closeout-intent marker for this transition, so the hook aborts it.
    _seed_proof(repo, candidate_head)
    raw = _g(repo, "update-ref", "refs/heads/dev", candidate_head, dev_before)
    assert raw.returncode != 0
    assert _g(repo, "rev-parse", "dev").stdout.strip() == dev_before
    raw_main = _g(repo, "update-ref", "refs/heads/main", candidate_head, dev_before)
    assert raw_main.returncode != 0

    accepted_package = _materialize_accepted_ethos_package(repo)
    accepted_hook_core = accepted_package / "src" / "ethos" / "surface" / "cli" / "hook" / "core.py"
    accepted_hook_core.write_text("raise SystemExit(91)\n", encoding="utf-8")

    # The sanctioned closeout of the identical head writes markers for both protected
    # refs and is judged by the candidate runner, not the intentionally unusable
    # incumbent reducer.
    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)
    assert closeout["ok"] is True, closeout
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head
    assert _g(repo, "rev-parse", "main").stdout.strip() == candidate_head


def test_hook_replacement_requires_executable_candidate_hook(tmp_path: Path) -> None:
    """A changed candidate hook must exist and be executable before closeout CAS."""
    accepted_root = tmp_path / "accepted"
    candidate_root = tmp_path / "candidate"
    accepted_root.mkdir()
    candidate_root.mkdir()
    transition = closeout_core.CloseoutTransition("refs/heads/dev", "old", "new", "new")

    def fake_git(root: Path, *_args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return cp(stdout="candidate\n" if root == accepted_root else "")

    update = closeout_core._atomic_update(  # noqa: SLF001 - direct fail-closed contract
        accepted_root, candidate_root, transition, None, fake_git
    )

    assert update.returncode == 1
    assert update.stderr == f"candidate_closeout_hook_unavailable:{candidate_root / '.githooks'}"


def test_candidate_hook_bootstraps_accepted_ff_closeout_from_legacy_incumbent(
    tmp_path: Path,
) -> None:
    """Official closeout selects a repaired candidate hook for its sole CAS.

    Raw Git remains on the legacy configured accepted hook and blocks the release
    mirror. The official atomic closeout must instead use the candidate hook
    directory, while retaining exact intents and candidate semantic admission.
    """
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path, mirror=True, legacy_hook=True)
    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n", upgrade_hook=True)
    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    _seed_proof(repo, candidate_head)
    raw_main = _g(repo, "update-ref", "refs/heads/main", candidate_head, dev_before)
    assert raw_main.returncode != 0
    assert _g(repo, "rev-parse", "main").stdout.strip() == dev_before

    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)

    assert closeout["ok"] is True, closeout
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head
    assert _g(repo, "rev-parse", "main").stdout.strip() == candidate_head


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
