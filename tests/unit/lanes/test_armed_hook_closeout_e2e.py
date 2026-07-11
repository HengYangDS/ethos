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
from ethos.adapters.mutation.lane_lifecycle.refresh import refresh_candidate_from_accepted
from ethos.adapters.mutation.proof import record_executed_proof
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease
from ethos.repository.evidence.core import EvidenceSet
from ethos.repository.policy.gates import promotion_required_gate_ids
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


def _armed_repo(tmp_path: Path) -> Path:
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
    _g(repo, "add", ".")
    _commit(repo, "init")
    _g(repo, "config", "core.hooksPath", ".githooks")
    _g(repo, "config", "ethos.acceptedBranch", "dev")
    _g(repo, "worktree", "add", "-b", "candidate/dev", str(tmp_path / "cand"), "dev")
    return repo


def _land_proven_work(repo: Path, tmp_path: Path, name: str, content: str) -> str:
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
    repo = _armed_repo(tmp_path)

    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n")
    assert _g(repo, "rev-parse", "candidate/dev").stdout.strip() == candidate_head

    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)
    assert closeout["ok"] is True, closeout
    assert closeout["state"] == "accepted_validated"
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head


def test_raw_ref_move_to_proven_head_is_blocked_without_marker(tmp_path: Path) -> None:
    """A hand-typed `git update-ref dev <candidate_head>` — proof present but NO one-shot
    closeout-intent marker — is aborted by the armed hook, while the sanctioned closeout of
    the very same head succeeds. This is the discrimination the removed env bypass used to
    defeat."""
    if not _HOOK_SRC.exists():
        return
    os.environ["ETHOS_ACTOR"] = "agent:test:case:agent-test"
    repo = _armed_repo(tmp_path)

    candidate_head = _land_proven_work(repo, tmp_path, "w", "hi\n")
    dev_before = _g(repo, "rev-parse", "dev").stdout.strip()
    # Even with a valid proof pre-placed at the accepted root, a raw ref move carries no
    # closeout-intent marker for this transition, so the hook aborts it.
    _seed_proof(repo, candidate_head)
    raw = _g(repo, "update-ref", "refs/heads/dev", candidate_head, dev_before)
    assert raw.returncode != 0
    assert _g(repo, "rev-parse", "dev").stdout.strip() == dev_before

    # The sanctioned closeout of the identical head writes the marker and is admitted.
    closeout = apply_candidate_to_accepted(root=repo, authorized=True, expect_head=dev_before)
    assert closeout["ok"] is True, closeout
    assert _g(repo, "rev-parse", "dev").stdout.strip() == candidate_head


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
