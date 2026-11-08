"""Check a raw push in CI, and name a protected peer that no push check covers.

The pre-push check reads what a push adds beyond its peer's advertisement, and a raw push bypasses
that hook. A GitLab job therefore checks the pushed range again with the job's own identity
variables, and the check is inert outside such a job. `status` names a protected peer under
`disabled`, or a mode it cannot read, as advisories only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.admission.peer_identity_push import added_literals
from ethos.adapters.admission.peer_identity_push import mode_at
from ethos.adapters.admission.peer_identity_push import tracking_base
from ethos.adapters.repo.peer_feed import ci_feed
from ethos.adapters.repo.peer_feed import peer_feed

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_ZERO = frozenset({"0" * 40, "0" * 64})


def peer_identity_backstop(
    repo: Path, *, proposed: str, remote_head: str, remote: str, environ: Mapping[str, str]
) -> dict[str, object]:
    """Check a raw push in CI: inert without the job's feed, refusing only under `required`."""
    feed = ci_feed(environ)
    if not feed:
        return {"verdict": "pass", "state": "inert", "required_gaps": [], "advisories": []}
    baseline = (
        remote_head if remote_head and remote_head not in _ZERO else tracking_base(repo, remote)
    )
    if not baseline:
        advisories = ["peer_identity_backstop_baseline_missing"]
        return {
            "verdict": "pass",
            "state": "baseline_missing",
            "required_gaps": [],
            "advisories": advisories,
        }
    if "required" not in {mode_at(repo, baseline), mode_at(repo, proposed)}:
        return {"verdict": "pass", "state": "disabled", "required_gaps": [], "advisories": []}
    gaps = added_literals(repo, proposed, (baseline,), feed)
    state = "refused" if gaps else "clean"
    return {
        "verdict": "block" if gaps else "pass",
        "state": state,
        "required_gaps": gaps,
        "advisories": [],
    }


def peer_identity_status(repo: Path) -> list[str]:
    """Return the `status` advisories: a protected peer left unchecked, or an unread mode.

    The count of literals outside the record roots is the redaction preview's to report: it reads
    the whole tracked tree, which took 10 s on ETHOS under load, too slow for every `status`.
    """
    if not peer_feed(repo):
        return []
    mode = mode_at(repo, "HEAD")
    if mode is None:
        return ["peer_identity_mode_unread"]
    return ["peer_identity_protected_peer_disabled"] if mode == "disabled" else []
