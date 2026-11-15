"""Follow the accepted branch's exact pin forward, and hold a lane's receipted departure from it.

`CURRENT` projects the release that the accepted branch pins. A transition without `--runtime`
selects that release's installed runtime only when it is newer than the selection, where a
development build precedes the release of its version; in every other state it leaves the selection
in place and names the state, and it fetches nothing. A lane that
selects another release with `--reason` leaves a receipt in the Git common directory; while the
accepted pin and the lane's ref last, the receipt holds the runtime it names.
"""

from __future__ import annotations

import json
import platform
import shlex
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING
from typing import NamedTuple

from packaging.version import Version

import ethos.adapters.repo.git as git
import ethos.adapters.repo.runtime.manifest as manifest
import ethos.contracts.branch.roles as roles
import ethos.repository.release.pin as pin
from ethos.adapters.repo.hook.rollback import RollbackRefusalError
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import run_mise

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.selection import SelectedRuntime

_RECEIPTS = "ethos/receipts/runtime-selection"
_REPAIR = (
    "in a lane, declare one exact pin, lock it with its attestation (mise lock) and land both; "
    "a clone with nothing selected first binds a runtime: ethos hook install --runtime <runtime>"
)


class PinSelection(NamedTuple):
    """What one transition does about the accepted pin, and the name of that state."""

    state: str = "followed"
    # The pinned release's install to select; with neither path the invoking build is selected.
    runtime: Path | None = None
    # The current selection, which this transition leaves in place.
    kept: Path | None = None
    next_action: str = ""

    def report(self) -> dict[str, str]:
        """Project the state and the action that settles it, empty where none is needed."""
        return {"state": self.state, "next_action": self.next_action}


def follow_accepted_pin(repo: Path, *, settle: bool = False) -> PinSelection:
    """Decide a transition without `--runtime`; only `settle` deletes the receipts it finds closed.

    A pin that cannot be selected never moves a selection: the transition keeps `CURRENT` and
    names why, so a lane can still start and repair the pin. With nothing selected it refuses.
    """
    config = _accepted_text(repo, MISE_CONFIG)
    # A configuration that never names the pin is read no further, whatever else it holds.
    if pin.PIN_KEY not in config:
        return PinSelection("runtime_pin_absent")
    common = Path(git.git_common_dir(repo))
    try:
        current = current_runtime(common)
    except (OSError, ValueError):
        current = None
    try:
        selection = _selection(repo, common, current, pin.declared_pin(config), settle=settle)
    except ValueError as error:
        # An unreadable pin or lock selects nothing; the reader's own gap names it.
        selection = PinSelection(str(error), next_action=_REPAIR)
    if selection.state == "runtime_pin_absent" or selection.runtime or selection.kept:
        return selection
    if current is None:
        raise RollbackRefusalError(selection.state, selection.next_action)
    return selection._replace(kept=current.root)


def _selection(
    repo: Path,
    common: Path,
    current: SelectedRuntime | None,
    declared: pin.DeclaredPin | None,
    *,
    settle: bool,
) -> PinSelection:
    """Name the pin's state; a state with neither path cannot select the pinned release."""
    if declared is None or declared.form != "github":
        return PinSelection("runtime_pin_absent")
    if current is not None:
        pinned, selected = Version(declared.version), Version(current.build.distribution_version)
        if _held(repo, common, declared.version, current.digest, settle=settle):
            return PinSelection("runtime_selection_open", kept=current.root)
        if pinned <= selected:
            behind = pinned < selected
            return PinSelection(
                "runtime_pin_behind_current" if behind else "followed",
                kept=current.root,
                next_action=_receipted(current.root) if behind else "",
            )
    # The lock is judged only here, where the transition would select the pinned bytes.
    entry = pin.lock_entry(_accepted_text(repo, MISE_LOCK), declared, mise_platform())
    if not _binds(entry, declared.version):
        return PinSelection("runtime_pin_unattested", next_action=_REPAIR)
    if installed := _installed(repo, f"{declared.key}@{declared.version}"):
        return PinSelection(runtime=installed)
    install = shlex.join(("mise", "--cd", repo.as_posix(), "install", "--locked"))
    return PinSelection("runtime_pin_not_installed", next_action=install)


def receipt_departure(repo: Path, target: SelectedRuntime, reason: str) -> dict[str, str]:
    """Record, before any effect, why a lane selects a release other than the accepted pin.

    Selecting the pinned release itself, or any release where the accepted branch pins none,
    departs from nothing and leaves no receipt. The receipt returned is read back from its file.
    """
    try:
        declared = pin.declared_pin(_accepted_text(repo, MISE_CONFIG))
    except ValueError:
        # No selection departs from a pin that cannot be read; every transition names it.
        declared = None
    if declared is None or declared.form != "github":
        return {}
    pinned, chosen = Version(declared.version), Version(target.build.distribution_version)
    if chosen == pinned:
        return {}
    lane = git.current_branch(repo)
    if not reason or roles.BranchRolePolicy().role_for_branch(lane) != roles.ROLE_WORK_LANE:
        gap = "runtime_selection_receipt_required"
        raise RollbackRefusalError(gap, _receipted(target.root))
    receipt = {
        "kind": "successor" if chosen > pinned else "rollback",
        "pin": declared.version,
        "selected": target.build.product_version,
        "runtime_digest": target.digest,
        "lane": lane,
        "reason": reason,
    }
    path = Path(git.git_common_dir(repo)) / _RECEIPTS / f"{declared.version}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    # A torn write is unreadable, which the next transition deletes as a closed receipt.
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    return json.loads(path.read_bytes())


def mise_platform() -> str:
    """Name this host as Mise keys a lock entry's platforms, as `linux-x64`."""
    system = platform.system().lower().replace("darwin", "macos")
    machine = manifest.canonical_architecture(manifest.process_machine())
    return f"{system}-{machine.replace('x86_64', 'x64')}"


def _accepted_text(repo: Path, path: str) -> str:
    """Read one tracked file from the accepted branch's tree; empty where it has none."""
    return git.committed_file_text(repo, roles.BranchRolePolicy().accepted_branch, path)


def _binds(entry: pin.LockEntry | None, version: str) -> bool:
    """Whether the platform's lock entry records what binds the release's bytes.

    That is the release's attestation, or its checksum where only checksums bind the release. An
    absent entry binds nothing in either class.
    """
    if entry is None:
        return False
    if pin.release_class(version) == "checksum":
        return entry.checksum != ""
    return entry.provenance == pin.ATTESTED_PROVENANCE


def _installed(repo: Path, tool: str) -> Path | None:
    """Ask Mise where the pinned release is installed; nothing is installed or fetched."""
    try:
        found = run_mise(
            repo, ("where", tool), files={MISE_CONFIG: "", MISE_LOCK: ""}, offline=True
        )
    except (OSError, ValueError):
        return None
    install = found.stdout.strip()
    if found.returncode or not install:
        return None
    generations = list(Path(install, "runtime").glob("*"))
    return generations[0].resolve() if len(generations) == 1 else None


def _held(repo: Path, common: Path, version: str, digest: str, *, settle: bool) -> bool:
    """Whether a lane's receipt holds this selection against this pin.

    A receipt is closed once the accepted pin is another, its lane's ref is gone or the selection
    is not the runtime it names.
    """
    for path in (common / _RECEIPTS).glob("*.json"):
        with suppress(OSError, ValueError, KeyError, TypeError):
            receipt = json.loads(path.read_bytes())
            named = path.stem, receipt["runtime_digest"]
            if named == (version, digest) and git.ref_head(repo, "refs/heads/" + receipt["lane"]):
                return True
        if settle:
            # A closed receipt holds nothing, so one that cannot be deleted blocks nothing.
            with suppress(OSError):
                path.unlink()
    return False


def _receipted(runtime: Path) -> str:
    """Render the install that records a departure; the lane and the reason are the operator's."""
    selected = shlex.quote(runtime.as_posix())
    return f"ethos hook install --runtime {selected} --reason <text> --root <lane> --json"
