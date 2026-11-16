"""Observe one head's hosted runs on every CI peer: an observation, which mints no authority.

A CI peer is a declared publication peer with the `ci_cd` capability. Each peer is read on its
own, so two peers that disagree stay two facts, and a repository that declares no CI peer has no
hosted plane to observe. The observation is read each time and stored nowhere.
"""

from __future__ import annotations

from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.mutation.publication.hosted_runs import observe_hosted_runs
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
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


def hosted_observation(root: Path, head: str) -> dict[str, object]:
    """Read each CI peer's runs of one exact commit and name every peer that did not pass."""
    try:
        topology = publication_topology(root, release_config(root))
    except ValueError as error:
        topology = {"required_gaps": [str(error)]}
    invalid = string_sequence(topology["required_gaps"])
    if invalid:
        # The topology names its own repair where it has one, and the observation keeps it;
        # every reader of the observation then has a step, the preview and the probe too.
        repair = {"next_action": str(topology.get("next_action") or "") or _DECLARATION}
        observed = {"head": head, "state": "topology_invalid", "peers": {}}
        return {**observed, "observation_gaps": invalid, **repair}
    peers = {
        str(peer["id"]): observe_hosted_runs(
            root, str(peer["git_remote"]), str(peer["provider"]), head
        )
        for peer in cast("list[dict[str, object]]", topology["remotes"])
        if "ci_cd" in string_sequence(peer["capabilities"])
    }
    states = {peer: str(observed["state"]) for peer, observed in peers.items()}
    found = set(states.values())
    # Every state but a pass is looked up, so a state that no gap names fails here and is not
    # dropped. The gaps then come in the order that decides: the first names the deciding peer.
    order = list(HOSTED_GAPS)
    named = [
        (f"{HOSTED_GAPS[state]}:{peer}", order.index(state))
        for peer, state in states.items()
        if state != "passed"
    ]
    return {
        "head": head,
        "state": next((state for state in HOSTED_GAPS if state in found), "passed")
        if peers
        else "no_ci_peer",
        "peers": peers,
        "observation_gaps": [gap for gap, _rank in sorted(named, key=itemgetter(1))],
    }
