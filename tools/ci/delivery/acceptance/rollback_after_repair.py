"""The journey's rollback after the declaration repair, as the product decides it.

After the retained upgrade returns, the lane holds the successor's repair. The successor's console
names the predecessor that the repository holds as its rollback, from that lane. The predecessor's
own publish readiness reads the lane's tree before anything is pinned or selected. One that reads
the repaired declaration is selected, and the selection then returns to the successor; one that
refuses it must leave the selector, the hooks and every retained byte as they were.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import named_runtime
from ethos.adapters.repo.worktree_list import parse_worktree_list
from tools.ci.delivery.acceptance import brownfield as brownfield_acceptance
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage

if TYPE_CHECKING:
    from collections.abc import Mapping

_REFUSED = "runtime_rollback_declaration_repaired"
# What this leg does not reach: a receipted departure from a pin, and a pin followed by landings.
_LEFT = {"receipted_rollback": "not_qualified", "pin_across_landings": "not_qualified"}


def _lane(repository: Path) -> Path:
    """Name the one linked Work Lane of the retained adopter, as Git registers it."""
    listed = run_git(repository, "worktree", "list", "--porcelain", "-z").stdout
    lanes = [
        Path(record["worktree"])
        for record in parse_worktree_list(listed)
        if record.get("branch", "").startswith("refs/heads/work/")
    ]
    if len(lanes) != 1:
        message = "package_rollback_after_repair_lane_missing"
        raise RuntimeError(message)
    return lanes[0]


def _select(
    console: Path, lane: Path, runtime: Path, *, environment: Mapping[str, str]
) -> tuple[list[str], str]:
    """Ask the console to select one installed runtime for the lane; return its gaps."""
    prefix = (str(console), *PYTHON_FLAGS, "-m", "ethos.cli")
    command = (*prefix, "hook", "install", "--runtime", str(runtime), "--root", str(lane), "--json")
    code, report, detail = invoke(lane, command, environment=environment)
    gaps = report.get("required_gaps")
    named = [str(gap) for gap in gaps] if isinstance(gaps, list) else []
    return named or (["package_rollback_after_repair_failed"] if code else []), detail


def _observed(repository: Path, selector: Path) -> tuple[object, ...]:
    """The retained repository, the selector, the hooks path and every hook file."""
    hooks = run_git(repository, "config", "--local", "--get", "core.hooksPath").stdout
    return (
        brownfield_acceptance.retained_repository(repository),
        selector.read_bytes(),
        hooks,
        runtime_file_inventory(Path(hooks.strip())),
    )


@observe_stage("rollback_after_repair")
def prove_rollback_after_repair(
    repository: Path, *, environment: Mapping[str, str]
) -> dict[str, object]:
    """Roll back from the repaired lane as the product decides it, then upgrade again."""
    common, lane = Path(git_common_dir(repository)), _lane(repository)
    successor, held = current_runtime(common), named_runtime(common, "ROLLBACK")
    if held is None:
        message = "package_rollback_after_repair_supply_missing"
        raise RuntimeError(message)
    selector = common / "ethos/runtime/CURRENT"
    before = _observed(repository, selector)
    gaps, detail = _select(successor.python, lane, held, environment=environment)
    if gaps == [_REFUSED]:
        if _observed(repository, selector) != before:
            message = "package_rollback_after_repair_refusal_changed_state"
            raise RuntimeError(message)
        return {"rollback_after_declaration_repair": "refused", **_LEFT}
    if gaps or current_runtime(common).root != held:
        message = f"package_rollback_after_repair_failed:{detail}"
        raise RuntimeError(message)
    if brownfield_acceptance.retained_repository(repository) != before[0]:
        message = "package_rollback_after_repair_retained_state_changed"
        raise RuntimeError(message)
    gaps, detail = _select(successor.python, lane, successor.root, environment=environment)
    if gaps or _observed(repository, selector) != before:
        message = f"package_rollback_after_repair_upgrade_failed:{detail}"
        raise RuntimeError(message)
    return {"rollback_after_declaration_repair": "admitted", **_LEFT}
