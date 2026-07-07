"""Shared CLI base — the App objects, type aliases, and cross-group helpers.

Every command-group module (surface/cli/<group>.py) and the top-level cli.py import
from here, so there is exactly ONE App object per group (registration is shared) and
the broadly-used _root/_emit helpers live in one place. This module imports only
downward (kernel/domain), never from cli.py or the group modules — keeping the
surface acyclic.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

if TYPE_CHECKING:
    from ethos_core.result import EthosResult

# ---- App objects (one per command group; commands register onto these) ----
app = App(name="ethos", help="ETHOS command plane.")
quality_app = App(name="quality", help="Quality and determinism checks.", show=False)
campaign_app = App(name="campaign", help="Evolution campaign commands.", show=False)
intake_app = App(name="intake", help="Intake ledger commands.", show=False)
assistants_app = App(name="assistants", help="Assistant and protocol projections.", show=False)
playbooks_app = App(name="playbooks", help="Repo-local skills and playbook routing.", show=False)
fleet_app = App(name="fleet", help="External adopter and fleet inspection.", show=False)
lane_app = App(name="lane", help="Work Lane lifecycle and write admission.", show=False)
hook_app = App(name="hook", help="Hook admission and guard reports.", show=False)
parity_app = App(name="parity", help="Capability parity and adopter shadow checks.", show=False)
rules_app = App(name="rules", help="Rules Product Kernel operations.", show=False)

for _sub in (
    quality_app,
    campaign_app,
    intake_app,
    assistants_app,
    playbooks_app,
    fleet_app,
    lane_app,
    hook_app,
    parity_app,
    rules_app,
):
    app.command(_sub)

# ---- shared parameter type aliases ----
JsonFlag = Annotated[bool, Parameter(name="--json")]
RootOption = Annotated[Path, Parameter(name="--root")]


# ---- cross-group helpers ----
def resolve_root(root: Path | None) -> Path:
    """Resolve the target repository root.

    The default is the current Git worktree root, not the process launch
    directory. Agent and IDE hosts often invoke ETHOS from a subdirectory inside a
    linked Work Lane; binding to that Work Lane's Git toplevel keeps relative
    paths, editor-root checks, and branch-role classification on the same
    governed subject. Non-Git adopters still resolve to the supplied path/cwd.
    """
    candidate = (root or Path.cwd()).resolve()
    completed = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=candidate,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return candidate


def sha256_file(path: Path) -> str:
    """Return the sha256:<hex> digest of a file (drift/attestation helper)."""
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def emit(result: EthosResult, json_output: bool, *, enforce: bool = True) -> None:
    """Print an EthosResult as JSON or a short human line, then enforce the verdict.

    Fail-CLOSED by default: a blocked verdict (result.ok is False) exits the process
    with a non-zero status AFTER printing — so every verdict is consumable by any
    caller (git hook, CI, MCP host, `&& deploy` chains) via exit status, not just
    readable as JSON. This is the edge that turns "reports a verdict" into "a process
    that refuses" (failure-blocking moves upstream).

    Read-only / report commands that legitimately return a non-ok scorecard WITHOUT
    refusing (status, plan, report, rules listing) must pass enforce=False EXPLICITLY
    — fail-open is the thing you opt into, in the open, per command. A new command
    inherits fail-closed by default, so a future verdict command cannot silently
    exit 0 on a block.
    """
    try:
        if json_output:
            print(result.to_json())
        else:
            print(f"{result.command}: {result.state}")
            for action in result.next_actions:
                print(f"next: {action}")
    except BrokenPipeError:
        return
    if enforce and not result.ok:
        raise SystemExit(1)


def load_command_groups(argv: list[str]) -> None:
    """Import only the command-group module the invocation needs (lazy startup).

    Each group registers its commands onto the shared *_app objects at import time;
    importing a group pulls that group's heavy deps. The common root commands
    (status/plan/prove/land/publish/report/...) live in this module and need no
    group, so a bare `ethos status` never loads the quality/repository graph. When a
    group sub-command is invoked (`ethos quality ...`, `ethos lane ...`), only that
    group is imported. With no recognizable group token (e.g. `--help`), all groups
    load so the full command surface is shown.
    """
    import importlib

    groups = (
        "fleet",
        "intake",
        "quality",
        "rules",
        "lane",
        "assistants",
        "campaign",
        "parity",
        "playbooks",
        "hook",
    )
    token = next((arg for arg in argv if not arg.startswith("-")), "")
    if token in groups:
        selected = [token]
    elif token:
        # A recognized root command (status/plan/prove/land/...) needs no group.
        selected = []
    else:
        # No command token (bare `ethos` / `ethos --help`): show the full surface.
        selected = list(groups)
    for name in selected:
        importlib.import_module(f"ethos.surface.cli.{name}")
