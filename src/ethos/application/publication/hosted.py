"""Observe one head's hosted runs on every CI peer: an observation, which mints no authority.

A CI peer is a declared publication peer with the `ci_cd` capability. Each peer is read on its
own, so two peers that disagree stay two facts, and a repository that declares no CI peer has no
hosted plane to observe. The observation is read each time and stored nowhere.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.publication.hosted_runs import observe_hosted_runs
from ethos.contracts.codes.gaps import repair_for
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# The gap that names each peer state other than a pass, in the order that decides the whole
# observation: a peer that failed or holds no run decides it, and one that is not readable or
# still running leaves it open.
HOSTED_GAPS = {
    "failed": "hosted_run_failed",
    "no_run": "hosted_run_missing",
    "unknown": "hosted_run_unknown",
    "running": "hosted_run_running",
}
OPEN_HOSTED_GAPS = frozenset({"hosted_run_unknown", "hosted_run_running"})
# The step for a publication declaration that cannot be observed and names no repair.
_DECLARATION = "repair the publication declaration, then observe again"


def _state(observed: Mapping[str, object]) -> str:
    """Read one peer's state; one that no gap names is unknown, never left out as a pass."""
    state = str(observed["state"])
    return state if state == "passed" or state in HOSTED_GAPS else "unknown"


def hosted_observation(root: Path, head: str) -> dict[str, object]:
    """Read each CI peer's runs of one exact commit and name every peer that did not pass."""
    try:
        topology = publication_topology(root, release_config(root))
    except ValueError as error:
        topology = {"required_gaps": [str(error)]}
    invalid = string_sequence(topology["required_gaps"])
    if invalid:
        # The topology's own repair comes first, then the registered repair of the first gap,
        # then a general step. The observation carries it, so each of its readers has a step,
        # the preview and the probe too.
        step = str(topology.get("next_action") or "") or repair_for(invalid[0]) or _DECLARATION
        observed = {"head": head, "state": "topology_invalid", "peers": {}}
        return {**observed, "observation_gaps": invalid, "next_action": step}
    peers = {
        str(peer["id"]): observe_hosted_runs(
            root, str(peer["git_remote"]), str(peer["provider"]), head
        )
        for peer in cast("list[dict[str, object]]", topology["remotes"])
        if "ci_cd" in string_sequence(peer["capabilities"])
    }
    states = {peer: _state(observed) for peer, observed in peers.items()}
    found = set(states.values())
    return {
        "head": head,
        "state": next((state for state in HOSTED_GAPS if state in found), "passed")
        if peers
        else "no_ci_peer",
        "peers": peers,
        # The gaps come in the order that decides, so the first names the deciding peer.
        "observation_gaps": [
            f"{gap}:{peer}"
            for state, gap in HOSTED_GAPS.items()
            for peer, read in states.items()
            if read == state
        ],
    }
