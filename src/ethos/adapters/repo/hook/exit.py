"""Apply or resume a previewed repository exit, inside one fence, or leave nothing changed.

The apply holds the runtime selection lock and the state database's write transaction, so no
Lease can start inside it. It recomputes the plan and requires the previewed digest, writes a
durable receipt and removes the record. It then writes each planned key only while the key still
holds its planned value, verifies that no worktree uses ETHOS's hooks, removes each selector only
while it holds its planned bytes, and marks the receipt applied. A failure attempts every
compensation step. Consumer records stay with the host store.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shlex
import sqlite3
from contextlib import ExitStack
from contextlib import closing
from contextlib import contextmanager
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from filelock import Timeout

import ethos.adapters.repo.config_effects as config_effects
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.hook.exit_plan import SELECTORS
from ethos.adapters.repo.hook.exit_plan import Values
from ethos.adapters.repo.hook.exit_plan import exit_preview
from ethos.adapters.repo.hook.preimage import ethos_owns_hooks_path
from ethos.adapters.repo.hook.preimage import exit_receipt_path
from ethos.adapters.repo.hook.preimage import file_bytes
from ethos.adapters.repo.hook.preimage import hooks_preimage_path
from ethos.adapters.repo.hook.preimage import restore_file
from ethos.adapters.repo.hook.preimage import write_json_atomically
from ethos.adapters.repo.runtime.retirement import retire_generations
from ethos.adapters.repo.runtime.selection import runtime_selection_lock
from ethos.adapters.store.state.schema import state_database
from ethos.repository.paradigm.parameters import seconds
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Generator

_PREVIEW = "ethos adopt --exit --json"
_Write = tuple[Path, str, str, list[str], list[str]]


def _remove(path: Path) -> None:
    path.unlink(missing_ok=True)


def _remove_selector(path: Path, planned: dict[str, Any]) -> None:
    """Remove a selector only while it still holds the bytes the plan named."""
    content = file_bytes(path)
    if content is None:
        return
    if hashlib.sha256(content).hexdigest() != planned.get("sha256"):
        message = f"adoption_exit_selector_changed:{path.name}"
        raise ValueError(message)
    _remove(path)


def _write_configuration(repo: Path, plan: dict[str, Any], written: list[_Write]) -> None:
    """Write worktree values while the extension still holds, then the common values."""
    planned = [
        (Path(path), "worktree", key, plan["worktrees"][path][key], values)
        for path, writes in plan["writes"]["worktrees"].items()
        for key, values in writes.items()
    ] + [
        (repo, "local", key, plan["common_current"][key], values)
        for key, values in plan["writes"]["common"].items()
    ]
    for path, scope, key, before, after in planned:
        config_effects.replace_config_values(
            path, {key: tuple(after)}, scope=scope, expected={key: tuple(before)}
        )
        written.append((path, scope, key, before, after))


def _require_no_ethos_hooks(common: Path, worktrees: dict[str, Values]) -> None:
    for worktree in worktrees:
        completed = run_git(Path(worktree), "config", "--get-all", "core.hooksPath", check=False)
        if completed.returncode not in {0, 1}:
            message = f"adoption_exit_hooks_path_unknown:{worktree}"
            raise ValueError(message)
        values = tuple(completed.stdout.splitlines()) if completed.returncode == 0 else ()
        if ethos_owns_hooks_path(common, values):
            message = f"adoption_exit_hooks_path_still_owned:{worktree}"
            raise ValueError(message)


def _mark_applied(path: Path) -> None:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    write_json_atomically(path, receipt | {"state": "applied"})


def _receipt(plan: dict[str, Any], prior: dict[str, bytes | None]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "state": "applying",
        "written_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "plan_digest": plan["plan_digest"],
        "selectors": {
            name: {
                "present": content is not None,
                **(
                    {
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "base64": base64.b64encode(content).decode("ascii"),
                    }
                    if content is not None
                    else {}
                ),
            }
            for name in SELECTORS
            for content in (prior[name],)
        },
        "configuration": {
            "before": {"common": plan["common_current"], "worktrees": plan["worktrees"]},
            "after": plan["after"],
        },
        "record": plan["record"],
    }


def _paths(common: Path) -> dict[str, Path]:
    return {
        **{name: common / "ethos" / "runtime" / name for name in SELECTORS},
        "record": hooks_preimage_path(common),
        "receipt": exit_receipt_path(common),
    }


def _compensate(
    plan: dict[str, Any],
    prior: dict[str, bytes | None],
    paths: dict[str, Path],
    written: list[_Write],
    reason: str,
) -> EthosResult:
    """Attempt every step back to the state before the exit, naming each one that fails."""
    failures: list[str] = []
    for path, scope, key, before, after in reversed(written):
        try:
            config_effects.replace_config_values(
                path, {key: tuple(before)}, scope=scope, expected={key: tuple(after)}
            )
        except (OSError, ValueError) as failure:
            failures.append(f"{key}:{failure}")
    for name, path in paths.items():
        try:
            restore_file(path, prior[name])
        except OSError as failure:
            failures.append(str(failure) or type(failure).__name__)
    if failures:
        return _result(
            plan,
            ("adoption_exit_compensation_failed:" + ";".join([reason, *failures]),),
            state="unknown",
            next_action=f"Inspect {paths['receipt']}; it names the state before the exit",
        )
    return _result(plan, (f"adoption_exit_failed:{reason}",), next_action=_PREVIEW)


@contextmanager
def _state_fence(repo: Path) -> Generator[None]:
    """Hold the Lease owner's write transaction, so no Lease starts while the exit applies.

    Without a state database no Lease exists; a lane start that creates one then adopts again
    through the selection lock, which waits for the exit.
    """
    database = state_database(repo)
    if not database.exists():
        yield
        return
    with closing(sqlite3.connect(database, timeout=seconds("lock"))) as connection:
        connection.execute("begin immediate")
        try:
            yield
        finally:
            connection.rollback()


def _apply(repo: Path, common: Path, expect_plan_digest: str) -> EthosResult:
    """Apply the previewed exit inside the selection lock and the state transaction."""
    with ExitStack() as stack:
        try:
            stack.enter_context(runtime_selection_lock(common))
        except Timeout:
            return _result({}, ("adoption_exit_selection_busy",), next_action=_PREVIEW)
        try:
            stack.enter_context(_state_fence(repo))
        except sqlite3.OperationalError:
            return _result({}, ("adoption_exit_state_busy",), next_action=_PREVIEW)
        return _apply_fenced(repo, common, expect_plan_digest)


def _apply_fenced(repo: Path, common: Path, expect_plan_digest: str) -> EthosResult:
    plan = exit_preview(repo)
    gaps = tuple(plan["required_gaps"])
    if not gaps and plan["plan_digest"] != expect_plan_digest:
        gaps = ("adoption_exit_plan_digest_mismatch",)
    if gaps:
        return _result(plan, gaps, next_action=_PREVIEW)
    paths = _paths(common)
    prior = {name: file_bytes(path) for name, path in paths.items()}
    written: list[_Write] = []
    try:
        if not plan["resume"]:
            write_json_atomically(paths["receipt"], _receipt(plan, prior))
        _remove(paths["record"])
        _write_configuration(repo, plan, written)
        _require_no_ethos_hooks(common, plan["worktrees"])
        for name in SELECTORS:
            _remove_selector(paths[name], plan["selectors"][name])
        _mark_applied(paths["receipt"])
    except (OSError, ValueError) as error:
        return _compensate(plan, prior, paths, written, str(error) or type(error).__name__)
    planned = frozenset(Path(path) for path in plan["generations"]["remove"])
    cleanup = retire_generations(repo, hooks=None, runtime=None, only=planned)
    kept = (entry["path"] for entry in plan["generations"]["keep"])
    residue = sorted({*cleanup["retained"], *cleanup.get("deferred", []), *kept})
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


def _decision(repo: Path, plan: dict[str, Any]) -> str:
    """The exact commands that settle an unrecorded hooks path, which ETHOS does not guess."""
    locations = [("--local", str(repo))] if "core.hooksPath" in plan["left"]["common"] else []
    locations += [
        ("--worktree", worktree)
        for worktree, left in plan["left"]["worktrees"].items()
        if "core.hooksPath" in left
    ]
    commands = "; ".join(
        shlex.join(("git", "-C", path, "config", scope, "--unset-all", "core.hooksPath"))
        for scope, path in locations
    )
    return (
        "No record names the hooks path that ETHOS replaced, and ETHOS does not guess it. "
        f"To use Git's default hooks, run: {commands}. To use your own hooks, set "
        f"core.hooksPath to their directory instead. Then run: {_PREVIEW}"
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
    try:
        common = Path(git_common_dir(repo)).resolve()
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
    preview = ("ethos", "adopt", "--exit", "--root", str(repo))
    exact = ("--apply", "--authorize", "--expect-head", head)
    request = (*exact, "--expect-plan-digest", plan["plan_digest"], "--json")
    next_action = (
        _decision(repo, plan)
        if "adoption_exit_preimage_unrecorded" in gaps
        else shlex.join((*preview, "--json") if gaps else (*preview, *request))
    )
    return _result(plan, gaps, next_action=next_action)
