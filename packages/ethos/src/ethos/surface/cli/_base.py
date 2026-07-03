"""Shared CLI base — the App objects, type aliases, and cross-group helpers.

Every command-group module (surface/cli/<group>.py) and the top-level cli.py import
from here, so there is exactly ONE App object per group (registration is shared) and
the broadly-used _root/_emit helpers live in one place. This module imports only
downward (kernel/domain), never from cli.py or the group modules — keeping the
surface acyclic.
"""

from __future__ import annotations

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

ASSISTANT_TRUTH_BOUNDARY = "repository-source-and-contracts"


# ---- cross-group helpers ----
def resolve_root(root: Path | None) -> Path:
    """Resolve the target repository root (cwd when unspecified)."""
    return (root or Path.cwd()).resolve()


def emit(result: EthosResult, json_output: bool, *, enforce: bool = False) -> None:
    """Print an EthosResult as JSON or a short human line.

    When enforce=True, a blocked verdict (result.ok is False) exits the process with
    a non-zero status AFTER printing — so an admission verdict is consumable by any
    caller (git hook, CI, MCP host) via exit status, not just readable as JSON. This
    is the edge that turns "reports a verdict" into "a process that refuses" (tao
    First Principle #2: failure-blocking moves upstream).
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
        return
