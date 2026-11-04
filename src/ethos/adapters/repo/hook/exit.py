"""Preview and apply a repository's exit from ETHOS's hook runtime.

An exit restores the Git configuration that adoption replaced, then removes the runtime selectors
and the record, so a repository leaves ETHOS without a guessed hooks path. The preview reports the
plan: the configuration now and what the recorded preimage restores, each linked worktree's own
values, the CURRENT and ROLLBACK selectors with their hashes, the Lease snapshot, the unlanded
topic branches, what blocks the exit, and a digest over all of them. It reads the state database
read-only and probes each lock without creating it.

The apply holds the runtime selection lock, recomputes the plan and requires the previewed digest.
It writes a receipt before the first effect, restores the configuration, verifies that no worktree
still uses ETHOS's hooks, and only then removes the selectors and the record; a failure restores
the prior state exactly. `retire_generations` then reclaims what it can prove unused, and each
generation it keeps is named as residue. Consumer records stay with the host store.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shlex
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from filelock import FileLock

import ethos.adapters.repo.config_effects as config_effects
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.activation import ACTIVATION_KEYS
from ethos.adapters.repo.hook.activation import WORKTREE_ACTIVATION_KEYS
from ethos.adapters.repo.hook.activation import linked_worktree_paths
from ethos.adapters.repo.hook.preimage import ethos_owns_hooks_path
from ethos.adapters.repo.hook.preimage import exit_receipt_path
from ethos.adapters.repo.hook.preimage import hooks_preimage_path
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from ethos.adapters.repo.hook.preimage import write_json_atomically
from ethos.adapters.repo.runtime.retirement import process_reference_paths
from ethos.adapters.repo.runtime.retirement import retire_generations
from ethos.adapters.repo.runtime.selection import runtime_selection_lock
from ethos.adapters.store.state.lease.projection import lease_observations
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.result import EthosResult

# ROLLBACK goes first, so an interrupted exit never leaves a rollback without its selection.
_SELECTORS = ("ROLLBACK", "CURRENT")
_Values = dict[str, list[str]]


def _selector(common: Path, name: str) -> dict[str, object]:
    path = common / "ethos" / "runtime" / name
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        return {"present": False}
    return {
        "present": True,
        "sha256": hashlib.sha256(content).hexdigest(),
        "names": content.decode("utf-8", "replace").strip(),
    }


def _held(lock: FileLock) -> bool:
    """Probe an existing lock without waiting; the probe never creates or unlinks its file.

    Taking a lock creates its file, so a missing file is a lock nobody holds. filelock's Timeout
    is an OSError, so a lock that cannot be taken, or whose state cannot be read, is held.
    """
    if not Path(lock.lock_file).is_file():
        return False
    try:
        with lock.acquire(blocking=False):
            return False
    except OSError:
        return True


def _blockers(repo: Path, common: Path, leases: list[dict[str, Any]]) -> list[str]:
    gaps = [
        f"adoption_exit_lease_live:{lease['subject']}"
        for lease in leases
        if lease["lease_state"] in {"valid", "unknown"}
    ]
    locks = (
        (runtime_selection_lock(common), "adoption_exit_selection_held"),
        (
            FileLock(
                common / "ethos" / "proof-slot.lock",
                fallback_to_soft=False,
                preserve_lock_file=True,
            ),
            "adoption_exit_proof_running",
        ),
    )
    gaps.extend(gap for lock, gap in locks if _held(lock))
    owned = ((common / "ethos" / "runtime").resolve(), (common / "ethos" / "hooks").resolve())
    try:
        references = process_reference_paths(repo)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return [*gaps, "adoption_exit_runtime_use_unknown"]
    if any(reference.is_relative_to(path) for reference in references for path in owned):
        gaps.append("adoption_exit_runtime_in_use")
    return gaps


def _unlanded(repo: Path) -> list[dict[str, str]]:
    """Name each topic branch whose head the accepted branch does not contain."""
    policy = load_branch_role_policy(repo)
    accepted = run_git(
        repo,
        "rev-parse",
        "--verify",
        "--quiet",
        f"refs/heads/{policy.accepted_branch}",
        check=False,
    ).stdout.strip()
    listed = run_git(
        repo,
        "for-each-ref",
        "--format=%(objectname) %(refname:lstrip=2)",
        "refs/heads",
        check=False,
    ).stdout.splitlines()
    return [
        {"branch": name, "head": head}
        for head, _, name in (line.partition(" ") for line in listed)
        if policy.is_topic_branch(name) and not (accepted and is_ancestor(repo, head, accepted))
    ]


def _ethos_hooks_remain(common: Path, current: _Values, worktrees: dict[str, _Values]) -> bool:
    return any(
        ethos_owns_hooks_path(common, tuple(values.get("core.hooksPath", ())))
        for values in (current, *worktrees.values())
    )


def exit_preview(root: Path) -> dict[str, Any]:
    """Plan the exit of one repository family; nothing is written."""
    repo = root.resolve()
    common = Path(git_common_dir(repo)).resolve()
    current = config_effects.config_values(repo, ACTIVATION_KEYS, scope="local")
    worktrees = {
        worktree.as_posix(): {
            key: list(values)
            for key, values in sorted(
                config_effects.config_values(
                    worktree, WORKTREE_ACTIVATION_KEYS, scope="worktree"
                ).items()
            )
        }
        for worktree in linked_worktree_paths(repo)
    }
    common_current = {key: list(values) for key, values in sorted(current.items())}
    selectors = {name: _selector(common, name) for name in _SELECTORS}
    ethos_hooks = _ethos_hooks_remain(common, common_current, worktrees)
    adopted = ethos_hooks or any(selector["present"] for selector in selectors.values())
    record = read_hooks_preimage(common) if adopted else None
    leases = sorted(
        (observation.record() for observation in lease_observations(state_database(repo))),
        key=lambda lease: str(lease["subject"]),
    )
    plan: dict[str, Any] = {
        "common_current": common_current,
        "restore": record,
        "worktrees": worktrees,
        "selectors": selectors,
        "leases": leases,
        "unlanded_branches": _unlanded(repo) if adopted else [],
        "consumer_records": "unchanged",
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    unrecorded = adopted and record is None and ethos_hooks
    gaps = ["adoption_exit_not_adopted"]
    if adopted:
        gaps = _blockers(repo, common, leases)
        gaps += ["adoption_exit_preimage_unrecorded"] if unrecorded else []
    return plan | {
        "plan_digest": hashlib.sha256(canonical).hexdigest(),
        "required_gaps": gaps,
        "user_decision_required": unrecorded,
    }


def _worktree_configuration_remains(plan: dict[str, Any], targets: dict[str, _Values]) -> bool:
    """Whether a worktree keeps its own configuration, which Git reads only with the extension."""
    if plan["common_current"].get("extensions.worktreeConfig") != ["true"]:
        return False
    owned = {key.lower() for key in WORKTREE_ACTIVATION_KEYS}
    for worktree in plan["worktrees"]:
        listed = run_git(
            Path(worktree), "config", "--worktree", "--name-only", "--list", check=False
        )
        if any(name.lower() not in owned for name in listed.stdout.split()):
            return True
    return any(any(values.values()) for values in targets.values())


def _targets(plan: dict[str, Any]) -> tuple[_Values | None, dict[str, _Values]]:
    """The configuration an exit writes: the record's, for the worktrees that still exist."""
    record = plan["restore"]
    if record is None:
        return None, {}
    worktrees = {
        path: record["worktrees"][path] for path in plan["worktrees"] if path in record["worktrees"]
    }
    common = {key: list(record["common"].get(key, [])) for key in ACTIVATION_KEYS}
    if _worktree_configuration_remains(plan, worktrees):
        common["extensions.worktreeConfig"] = ["true"]
    return common, worktrees


def _write_configuration(repo: Path, common: _Values | None, worktrees: dict[str, _Values]) -> None:
    """Write worktree values while the extension still holds, then the common values."""
    for path, values in worktrees.items():
        config_effects.replace_config_values(
            Path(path),
            {key: tuple(values.get(key, ())) for key in WORKTREE_ACTIVATION_KEYS},
            scope="worktree",
        )
    if common is not None:
        config_effects.replace_config_values(
            repo, {key: tuple(common.get(key, ())) for key in ACTIVATION_KEYS}, scope="local"
        )


def _require_no_ethos_hooks(common: Path, worktrees: dict[str, _Values]) -> None:
    for worktree in worktrees:
        completed = run_git(Path(worktree), "config", "--get-all", "core.hooksPath", check=False)
        values = tuple(completed.stdout.splitlines()) if completed.returncode == 0 else ()
        if ethos_owns_hooks_path(common, values):
            message = f"adoption_exit_hooks_path_still_owned:{worktree}"
            raise ValueError(message)


def _remove(path: Path) -> None:
    path.unlink(missing_ok=True)


def _bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _put(path: Path, content: bytes | None) -> None:
    """Return one file to exact prior bytes, or to its absence."""
    if content is None:
        path.unlink(missing_ok=True)
    elif _bytes(path) != content:
        staged = path.with_name(f".{path.name}-restore")
        staged.write_bytes(content)
        staged.replace(path)


def _receipt(
    plan: dict[str, Any], prior: dict[str, bytes | None], after: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "state": "applying",
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "plan_digest": plan["plan_digest"],
        "selectors": {
            name: {
                "present": prior[name] is not None,
                **(
                    {
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "base64": base64.b64encode(content).decode("ascii"),
                    }
                    if (content := prior[name]) is not None
                    else {}
                ),
            }
            for name in _SELECTORS
        },
        "configuration": {
            "before": {"common": plan["common_current"], "worktrees": plan["worktrees"]},
            "after": after,
        },
        "record": plan["restore"],
    }


def _paths(common: Path) -> dict[str, Path]:
    return {
        **{name: common / "ethos" / "runtime" / name for name in _SELECTORS},
        "record": hooks_preimage_path(common),
        "receipt": exit_receipt_path(common),
    }


def _compensate(
    repo: Path, common: Path, plan: dict[str, Any], prior: dict[str, bytes | None], reason: str
) -> EthosResult:
    """Return configuration, selectors, record and receipt to the state before the exit."""
    try:
        config_effects.replace_config_values(
            repo,
            {key: tuple(plan["common_current"].get(key, ())) for key in ACTIVATION_KEYS},
            scope="local",
        )
        _write_configuration(repo, None, plan["worktrees"])
        for name, path in _paths(common).items():
            _put(path, prior[name])
    except (OSError, ValueError) as failure:
        return _result(
            plan,
            (f"adoption_exit_compensation_failed:{failure}",),
            state="unknown",
            next_action=f"Inspect {exit_receipt_path(common)}; it names the state before the exit",
        )
    return _result(
        plan,
        (f"adoption_exit_failed:{reason}",),
        next_action="ethos adopt --exit --json",
    )


def _apply(repo: Path, common: Path, expect_plan_digest: str) -> EthosResult:
    """Apply the previewed exit in the reviewed order under the runtime selection lock."""
    with runtime_selection_lock(common):
        plan = exit_preview(repo)
        gaps = tuple(plan["required_gaps"])
        if not gaps and plan["plan_digest"] != expect_plan_digest:
            gaps = ("adoption_exit_plan_digest_mismatch",)
        if gaps:
            return _result(plan, gaps, next_action="ethos adopt --exit --json")
        paths = _paths(common)
        prior = {name: _bytes(path) for name, path in paths.items()}
        common_target, worktree_targets = _targets(plan)
        after = {"common": common_target, "worktrees": worktree_targets}
        receipt = _receipt(plan, prior, after)
        write_json_atomically(paths["receipt"], receipt)
        try:
            _write_configuration(repo, common_target, worktree_targets)
            _require_no_ethos_hooks(common, plan["worktrees"])
            for name in (*_SELECTORS, "record"):
                _remove(paths[name])
        except (OSError, ValueError) as error:
            return _compensate(repo, common, plan, prior, str(error) or type(error).__name__)
        write_json_atomically(paths["receipt"], receipt | {"state": "applied"})
        cleanup = retire_generations(repo, hooks=None, runtime=None)
    residue = sorted({*cleanup["retained"], *cleanup.get("deferred", [])})
    return _result(
        plan | {"receipt": paths["receipt"].as_posix(), "generation_cleanup": cleanup},
        (),
        state="applied",
        next_action="ethos status --json",
        residue=residue,
    )


def _result(
    plan: dict[str, Any],
    gaps: tuple[str, ...],
    *,
    state: str = "",
    next_action: str = "",
    residue: list[str] | None = None,
) -> EthosResult:
    resolved = state or ("blocked" if gaps else "planned")
    return EthosResult(
        command="adopt",
        verdict="unknown" if resolved == "unknown" else "block" if gaps else "pass",
        state=resolved,
        required_gaps=gaps,
        next_action=next_action,
        user_decision_required=bool(plan.get("user_decision_required"))
        or "authorization_required" in gaps
        or resolved == "planned",
        data=plan | ({"residue": residue} if residue is not None else {}),
    )


def adopt_exit(
    root: Path,
    *,
    head: str,
    request_gaps: tuple[str, ...] = (),
    apply: bool = False,
    expect_plan_digest: str | None = None,
) -> EthosResult:
    """Preview a repository's exit, or apply exactly the previewed plan."""
    repo = root.resolve()
    common = Path(git_common_dir(repo)).resolve()
    try:
        plan = exit_preview(repo)
    except (OSError, ValueError) as error:
        return EthosResult(
            command="adopt",
            verdict="unknown",
            state="unknown",
            required_gaps=(f"adoption_exit_observation_failed:{error}",),
            next_action=shlex.join(("ethos", "adopt", "--exit", "--root", str(repo), "--json")),
        )
    digest_gaps = (
        ()
        if not apply
        else ("adoption_exit_plan_digest_required",)
        if expect_plan_digest is None
        else ("adoption_exit_plan_digest_mismatch",)
        if expect_plan_digest != plan["plan_digest"]
        else ()
    )
    gaps = (*request_gaps, *plan["required_gaps"], *digest_gaps)
    if apply and not gaps and expect_plan_digest is not None:
        return _apply(repo, common, expect_plan_digest)
    exact = ("--apply", "--authorize", "--expect-head", head)
    request = (*exact, "--expect-plan-digest", plan["plan_digest"], "--json")
    preview = ("ethos", "adopt", "--exit", "--root", str(repo))
    return _result(
        plan,
        gaps,
        next_action=shlex.join((*preview, "--json") if gaps else (*preview, *request)),
    )
