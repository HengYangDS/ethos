"""Git IO adapter — subprocess primitives for reading Git facts and wiring hooks.

The impure IO shell for Git: every function shells out to `git`. Product domain
code stays pure and is fed these facts by the surface/orchestration layer. Reads
dominate; the one sanctioned write is hook-path wiring (set_hooks_path), which
installs the local admission entrance.
"""

from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import Attestation


def current_head(root: Path) -> str:
    """Return the current HEAD sha, or 'untracked' if not a resolvable ref."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        # root does not exist (e.g. a stale or foreign target path): treat as untracked
        # rather than crashing — the caller reports a gap, not an exception.
        return "untracked"
    if completed.returncode != 0:
        return "untracked"
    return completed.stdout.strip()


def current_tracked_head(root: Path) -> str:
    """Return the current HEAD sha, or '' when untracked."""
    head = current_head(root)
    return "" if head == "untracked" else head


def current_tree(root: Path, head: str = "HEAD") -> str:
    """Return the exact tree for a Git revision, or an empty string on failure."""
    return git_stdout(root, "rev-parse", f"{head}^{{tree}}")


def git_stdout_checked(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stdout, raising on failure."""
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.rstrip("\n")


def git_stdout(root: Path, *args: str) -> str:
    """Run `git <args>` in root and return stripped stdout, or '' on failure."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        # root does not exist: no git facts to read, same as a failed command.
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def committed_file_text(root: Path, ref: str, path: str) -> str:
    """Return a tracked file's text from a committed tree, or '' when unavailable."""
    return git_stdout(root, "show", f"{ref}:{path}") if ref else ""


def remote_tracking_sync(root: Path, branch: str, remote: str = "origin") -> dict[str, object]:
    """Project local HEAD versus the local remote-tracking ref without network IO."""
    branch_name = branch.strip()
    remote_name = remote.strip() or "origin"
    remote_ref = f"{remote_name}/{branch_name}" if branch_name else remote_name
    result: dict[str, object] = {
        "kind": "git_remote_tracking_sync",
        "remote": remote_name,
        "branch": branch_name,
        "remote_ref": remote_ref,
        "local_head": current_tracked_head(root),
        "remote_head": "",
        "ahead": 0,
        "behind": 0,
        "available": False,
        "blocking": False,
        "required_gaps": [],
    }
    if not branch_name:
        return {
            **result,
            "state": "branch_unknown",
            "advisory_gaps": ["remote_tracking_branch_unknown"],
        }
    remote_head = git_stdout(root, "rev-parse", "--verify", remote_ref)
    if not remote_head:
        return {
            **result,
            "state": "remote_tracking_missing",
            "advisory_gaps": [f"remote_tracking_missing:{remote_ref}"],
        }
    counts = git_stdout(root, "rev-list", "--left-right", "--count", f"{remote_ref}...HEAD")
    try:
        behind_text, ahead_text = counts.split()[:2]
        behind, ahead = int(behind_text), int(ahead_text)
    except (IndexError, ValueError):
        behind = ahead = 0
    state = (
        "diverged"
        if ahead and behind
        else "local_ahead"
        if ahead
        else "local_behind"
        if behind
        else "synchronized"
    )
    result.update(
        state=state,
        remote_head=remote_head,
        ahead=ahead,
        behind=behind,
        available=True,
        advisory_gaps=[]
        if state == "synchronized"
        else [f"remote_tracking_{state}:{remote_ref}:{ahead}:{behind}"],
    )
    return result


def publication_remote_syncs(root: Path, branch: str) -> dict[str, object]:
    """Project configured GitLab/GitHub branches without granting either authority."""
    records: dict[str, dict[str, object]] = {}
    configured = set(git_stdout(root, "remote").splitlines())
    for remote in ("origin", "github"):
        if remote not in configured:
            continue
        records[remote] = remote_tracking_sync(root, branch, remote)
    states = {str(record.get("state") or "not_checked") for record in records.values()}
    synchronized = bool(records) and states == {"synchronized"}
    reconciliation_required = any(
        state in {"diverged", "local_behind", "remote_tracking_missing"} for state in states
    )
    return {
        "remotes": records,
        "state": "synchronized"
        if synchronized
        else "reconciliation_required"
        if reconciliation_required
        else "pending",
        "advisory_gaps": [
            f"remote_reconciliation_required:{name}:{record.get('state')}"
            for name, record in records.items()
            if record.get("state") != "synchronized"
        ],
    }


def set_hooks_path(root: Path, hooks_path: str) -> bool:
    """Wire git core.hooksPath to hooks_path (the sanctioned local-entrance write)."""
    completed = subprocess.run(
        ["git", "config", "core.hooksPath", hooks_path],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def set_config(root: Path, key: str, value: str) -> bool:
    """Set a local git config key (used to record ethos.acceptedBranch for the hooks)."""
    completed = subprocess.run(
        ["git", "config", key, value],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def git_common_dir(root: Path) -> str:
    """Return the resolved git common dir (shared across worktrees), or ''."""
    common_dir = git_stdout(root, "rev-parse", "--git-common-dir")
    if not common_dir:
        return ""
    path = Path(common_dir)
    if not path.is_absolute():
        path = root / path
    return path.resolve().as_posix()


def same_git_repository(left: Path, right: Path) -> bool:
    """True when both paths resolve to the same underlying git repository."""
    left_common = git_common_dir(left)
    right_common = git_common_dir(right)
    return bool(left_common and right_common and left_common == right_common)


def git_files(root: Path, *patterns: str) -> list[str]:
    """Return tracked files matching the given pathspec patterns."""
    command = ["git", "ls-files", *patterns]
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line]


def commits_equivalent_over_paths(
    root: Path,
    head: str,
    *,
    relevant_paths: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the commits parity-equivalent to head over a set of relevant pathspecs.

    A commit is "equivalent" to head when nothing under relevant_paths changed between
    it and head — so head's parity/shadow verdict is unchanged from that commit. Git
    cannot express "commits that did NOT touch a pathspec", so we find the boundary
    (the most recent commit at-or-before head that DID touch a relevant path) and
    return everything from that boundary (exclusive) up to head, plus head itself.

    When no relevant path was ever touched in head's history the boundary is empty; we
    then return just (head,) — the caller keeps its own parent handling for that case.
    """
    if not head:
        return ()
    boundary = git_stdout(root, "rev-list", "-1", head, "--", *relevant_paths)
    if not boundary:
        # No relevant path exists anywhere in head's history — nothing that could
        # change the parity verdict was ever committed, so every reachable commit is
        # parity-equivalent to head.
        span = git_stdout(root, "rev-list", head)
        return tuple(dict.fromkeys(line for line in span.splitlines() if line)) or (head,)
    if boundary == head:
        # head itself changed a relevant path — only head is current.
        return (head,)
    # boundary is the most recent commit that changed a relevant path; nothing relevant
    # changed after it, so boundary's source state equals head's. Every commit from
    # boundary (inclusive) up to head is therefore parity-equivalent to head.
    span = git_stdout(root, "rev-list", f"{boundary}..{head}")
    commits = [line for line in span.splitlines() if line]
    return tuple(dict.fromkeys([head, *commits, boundary]))


def remote_availability(
    root: Path, remote: str = "origin", *, timeout_seconds: float = 3.0
) -> dict[str, object]:
    """Probe whether a configured Git remote is reachable without mutating state."""
    url = git_stdout(root, "remote", "get-url", remote)
    if not url:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "state": "unconfigured",
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [f"remote_unconfigured:{remote}"],
        }
    try:
        completed = subprocess.run(
            ["git", "ls-remote", "--exit-code", remote],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "url": url,
            "state": "unavailable",
            "available": False,
            "blocking": False,
            "reason": "timeout",
            "stderr": str(exc),
            "required_gaps": [],
            "advisory_gaps": [f"remote_unavailable:{remote}"],
        }
    if completed.returncode == 0:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "url": url,
            "state": "available",
            "available": True,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
        }
    return {
        "kind": "git_remote_availability",
        "remote": remote,
        "url": url,
        "state": "unavailable",
        "available": False,
        "blocking": False,
        "reason": "ls_remote_failed",
        "exit_code": completed.returncode,
        "stderr": completed.stderr.strip(),
        "required_gaps": [],
        "advisory_gaps": [f"remote_unavailable:{remote}"],
    }


def remote_availability_not_probed(root: Path, remote: str = "origin") -> dict[str, object]:
    """Describe a configured remote without performing a network reachability probe."""
    url = git_stdout(root, "remote", "get-url", remote)
    if not url:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "state": "unconfigured",
            "available": False,
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [f"remote_unconfigured:{remote}"],
        }
    return {
        "kind": "git_remote_availability",
        "remote": remote,
        "url": url,
        "state": "not_probed",
        "available": False,
        "blocking": False,
        "required_gaps": [],
        "advisory_gaps": [],
    }


def execute_git_effect(
    root: Path,
    effect: GitEffect,
    *,
    issuer: str,
    attestations: tuple[Attestation, ...] = (),
) -> Attestation:
    """Execute, recover, or replay one exact Git ref transaction."""
    digest = effect.digest()
    matching = tuple(attestation for attestation in attestations if attestation.id == effect.id)
    if matching:
        if any(
            attestation.kind != "git-effect"
            or attestation.subject != effect.plan_digest
            or attestation.content.get("effect_digest") != digest
            for attestation in matching
        ):
            raise ValueError("git_effect_identity_collision")
        attestation = matching[-1]
        if any(_effect_ref(root, ref) != value for ref, value in effect.assertions.items()):
            raise ValueError("git_effect_cas_mismatch")
        if any(_effect_ref(root, ref) != update.desired for ref, update in effect.updates.items()):
            raise ValueError("git_effect_postcondition_failed")
        return attestation
    observed = {ref: _effect_ref(root, ref) for ref in effect.updates}
    if any(_effect_ref(root, ref) != value for ref, value in effect.assertions.items()):
        raise ValueError("git_effect_cas_mismatch")
    desired = {ref: update.desired for ref, update in effect.updates.items()}
    if observed == desired:
        return _attestation(effect, issuer=issuer, state="recovered")
    expected = {ref: update.expected for ref, update in effect.updates.items()}
    if observed != expected:
        raise ValueError("git_effect_cas_mismatch")
    program = "\0".join(
        (
            "start",
            *(
                token
                for ref, value in effect.assertions.items()
                for token in (f"update {ref}", value, value)
            ),
            *(
                token
                for ref, update in effect.updates.items()
                for token in (f"update {ref}", update.desired, update.expected)
            ),
            "prepare",
            "commit",
            "",
        )
    )
    completed = subprocess.run(
        ["git", "update-ref", "--stdin", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
        input=program,
        text=True,
    )
    if completed.returncode:
        raise ValueError("git_effect_cas_rejected")
    if {ref: _effect_ref(root, ref) for ref in effect.updates} != desired:
        raise ValueError("git_effect_postcondition_failed")
    return _attestation(effect, issuer=issuer, state="applied")


def git_effect_attestations(
    root: Path,
    effect_id: str,
    record: Attestation | None = None,
) -> tuple[Attestation, ...]:
    path = Path(git_common_dir(root), "ethos", "git-effects", f"{effect_id.replace(':', '-')}.json")
    if record is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json(), encoding="utf-8")
        return (record,)
    try:
        return (Attestation.model_validate_json(path.read_text(encoding="utf-8")),)
    except (OSError, ValueError):
        return ()


def git_ref_effect(
    effect_id: str,
    plan_digest: str,
    transitions: tuple[object, ...],
    assertions: dict[str, str],
) -> GitEffect:
    """Build one exact ref effect from transition-shaped records."""
    updates = {
        str(item.ref_name): GitRefUpdate(expected=str(item.old_value), desired=str(item.new_value))
        for item in transitions
    }
    return GitEffect(
        id=effect_id,
        plan_digest=plan_digest,
        updates=updates,
        assertions=assertions,
    )


def git_effect_plan_digest(root: Path, head: str) -> str:
    from ethos.adapters.mutation.proof import executed_proof_record
    from ethos.adapters.mutation.proof import proof_plan_digest

    record = executed_proof_record(root, head)
    value = str(record.get("plan_digest") or "") if record else ""
    if len(value) != 64 or value != proof_plan_digest(root):
        raise ValueError("git_effect_plan_digest_missing")
    return value


def sync_linked_ref_worktree(
    worktrees: list[dict[str, object]],
    branch: str,
    head: str,
    previous: str,
) -> dict[str, object]:
    """Synchronize a linked ref worktree after its ref transaction."""
    if not branch:
        return {"mode": "independent", "worktree_sync": "not_enabled"}
    path = next(
        (
            Path(str(item["path"]))
            for item in worktrees
            if item.get("branch") == branch
            and item.get("worktree_binding") in {"current", "linked"}
        ),
        None,
    )
    result = {
        "mode": "accepted_ff",
        "branch": branch,
        "previous_head": previous,
        "head": head,
        "worktree_sync": "not_linked" if path is None else "synced",
    }
    if path is None:
        return result
    reset = subprocess.run(
        ["git", "reset", "--hard", head],
        cwd=path,
        check=False,
        capture_output=True,
        text=True,
    )
    if reset.returncode:
        return {**result, "worktree_sync": "failed", "stderr": reset.stderr.strip()}
    return {
        **result,
        "worktree_sync": (
            "dirty"
            if subprocess.run(
                ["git", "status", "--short"],
                cwd=path,
                check=False,
                capture_output=True,
                text=True,
            ).stdout.strip()
            else "synced"
        ),
    }


def sync_current_worktree(root: Path, head: str) -> dict[str, object]:
    reset = subprocess.run(
        ["git", "reset", "--hard", head],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if reset.returncode and any(
        token in reset.stderr.lower() for token in ("index.lock", "could not lock index")
    ):
        reset = subprocess.run(
            ["git", "reset", "--hard", head],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    if reset.returncode:
        return {"state": "failed", "stderr": reset.stderr.strip()}
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "state": "dirty" if status.returncode or status.stdout.strip() else "synced",
        "status": status.stdout.strip(),
        "stderr": status.stderr.strip(),
    }


def reference_transaction_hook_changed(
    root: Path,
    accepted_head: str,
    candidate_head: str,
) -> bool:
    path = ".githooks/reference-transaction"
    entries = [
        subprocess.run(
            ["git", "ls-tree", head, path],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for head in (accepted_head, candidate_head)
    ]
    if not entries[1].startswith("100755 blob "):
        raise ValueError("release_mirror_candidate_hook_invalid")
    return entries[0] != entries[1]


def _effect_ref(root: Path, ref: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _attestation(effect: GitEffect, *, issuer: str, state: str) -> Attestation:
    return Attestation(
        id=effect.id,
        kind="git-effect",
        issuer=issuer,
        subject=effect.plan_digest,
        issued_at=datetime.now(UTC),
        content={
            "effect_digest": effect.digest(),
            "state": state,
            "updates": effect.model_dump(mode="json")["updates"],
        },
    )
