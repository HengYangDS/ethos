"""Shared CLI base — the App objects, type aliases, and cross-group helpers.

Every command-group module (surface/cli/<group>.py) and the top-level cli.py import
from here, so there is exactly ONE App object per group (registration is shared) and
the broadly-used _root/_emit helpers live in one place. This module imports only
downward (kernel/domain), never from cli.py or the group modules — keeping the
surface acyclic.
"""

from __future__ import annotations

import hashlib
import importlib
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

from ethos.result import EthosResult
from ethos.result import apply_payload_budget

# ---- App objects (one per command group; commands register onto these) ----
app = App(name="ethos", help="ETHOS command plane.")
campaign_app = App(name="campaign", help="Evolution campaign commands.", show=False)
intake_app = App(name="intake", help="Intake ledger commands.", show=False)
assistants_app = App(name="assistants", help="Assistant and protocol projections.", show=False)
playbooks_app = App(name="playbooks", help="Repo-local skills and playbook routing.", show=False)
fleet_app = App(name="fleet", help="External adopter and fleet inspection.", show=False)
lane_app = App(name="lane", help="Work Lane lifecycle and write admission.", show=False)
lane_lease_app = App(name="lease", help="Generation-bound local Lane Lease lifecycle.")
lane_handoff_app = App(name="handoff", help="Local and cross-host Work Lane handoff.")
lane_resolution_app = App(name="resolution", help="Exceptional Work Lane judgment and repair.")
lane_retire_app = App(name="retire", help="Bounded Work Lane retirement lifecycle.")
lane_app.command(lane_lease_app)
lane_app.command(lane_handoff_app)
lane_app.command(lane_resolution_app)
lane_app.command(lane_retire_app)
hook_app = App(name="hook", help="Hook admission and guard reports.", show=False)
parity_app = App(name="parity", help="Capability parity and adopter shadow checks.", show=False)
rules_app = App(name="rules", help="Rules Product Kernel operations.", show=False)

for _sub in (
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
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=candidate,
            text=True,
            capture_output=True,
            check=False,
        )
    except (FileNotFoundError, NotADirectoryError):
        return candidate
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return candidate


def emit_invalid_adopter_profile(*, command: str, json_output: bool, enforce: bool) -> None:
    """Emit the stable fail-closed envelope for an invalid adopter binding."""
    result = EthosResult(
        command=command,
        ok=False,
        state="gapped",
        required_gaps=("adopter_profile_invalid:.ethos/profile.toml",),
        next_actions=("repair .ethos/profile.toml and rerun the command",),
        data={"error_boundary": "adopter_profile_validation"},
    )
    emit(result, json_output=json_output, enforce=enforce)


def sha256_file(path: Path) -> str:
    """Return the sha256:<hex> digest of a file (drift/attestation helper)."""
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def emit(
    result: EthosResult,
    *,
    json_output: bool,
    enforce: bool = True,
    artifact_root: Path | None = None,
) -> None:
    """Print an EthosResult as JSON or a short human line, then enforce the verdict.

    Fail-CLOSED by default: a blocked verdict (result.ok is False) exits the process
    with a non-zero status AFTER printing — so every verdict is consumable by any
    caller (git hook, CI, MCP host, `&& deploy` chains) via exit status, not just
    readable as JSON. This is the edge that turns "reports a verdict" into "a process
    that refuses" (failure-blocking moves upstream).

    Read-only commands that legitimately return a non-ok result WITHOUT refusing
    (status, plan, rules listing) must pass enforce=False EXPLICITLY
    — fail-open is the thing you opt into, in the open, per command. A new command
    inherits fail-closed by default, so a future verdict command cannot silently
    exit 0 on a block.
    """
    if json_output and artifact_root is not None:
        result = apply_payload_budget(result, root=artifact_root)
    try:
        if json_output:
            sys.stdout.write(f"{result.to_json()}\n")
        else:
            sys.stdout.write(f"{result.command}: {result.state}\n")
            for action in result.next_actions:
                sys.stdout.write(f"next: {action}\n")
    except (BrokenPipeError, BlockingIOError):
        return
    if enforce and not result.ok:
        raise SystemExit(1)


def load_command_groups(argv: list[str]) -> None:
    """Load only the command-group registration needed by this invocation.

    Command functions own their Cyclopts declaration. This loader imports only
    the module selected by the first command token; bare help imports all modules.
    """
    modules = {
        "status": "ethos.surface.cli.root.inspection",
        "doctor": "ethos.surface.cli.root.inspection",
        "plan": "ethos.surface.cli.root.planning",
        "prove": "ethos.surface.cli.root.proof",
        "land": "ethos.surface.cli.root.lifecycle",
        "publish": "ethos.surface.cli.root.lifecycle",
        "adopt": "ethos.surface.cli.root.adoption",
        "explain": "ethos.surface.cli.root.reference",
        "docs": "ethos.surface.cli.root.reference",
        "audit": "ethos.surface.cli.root.reference",
        "openspec": "ethos.surface.cli.root.reference",
        "fleet": "ethos.surface.cli.fleet",
        "intake": "ethos.surface.cli.intake",
        "rules": "ethos.surface.cli.rules",
        "lane": "ethos.surface.cli.lane.core",
        "assistants": "ethos.surface.cli.assistants",
        "campaign": "ethos.surface.cli.campaign",
        "parity": "ethos.surface.cli.parity.core",
        "playbooks": "ethos.surface.cli.playbooks",
        "hook": "ethos.surface.cli.hook.core",
    }
    token = next((arg for arg in argv if not arg.startswith("-")), "")
    if token in modules:
        selected = (modules[token],)
    elif token:
        selected = ()
    else:
        selected = tuple(dict.fromkeys(modules.values()))
    for module in selected:
        importlib.import_module(module)
        if module == modules["lane"]:
            importlib.import_module("ethos.surface.cli.lane.lease")
            importlib.import_module("ethos.surface.cli.lane.resolution")
