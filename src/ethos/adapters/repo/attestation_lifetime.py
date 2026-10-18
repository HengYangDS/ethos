"""One lifetime per selected Attestation member, ended only by positive evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Literal

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence
    from datetime import datetime

    from ethos.contracts.semantic import Attestation

Lifetime = Literal["operation", "head", "lineage", "window", "open-predicate"]

_LANE_SUBJECT_TRANSITIONS = frozenset({"lane.start", "lane.start.compensate", "lane.retire"})
_LANE_EXECUTION_TRANSITIONS = frozenset(
    {"lane.refresh", "lane.merge", "commit.checkpoint", "maintainer.recover", "openspec.archive"}
)
_LANE_REF_TRANSITIONS = frozenset({"commitment.rebind", "v1-to-v2-bootstrap"})
_HEAD_BRANCH_FIELDS = {
    "candidate.integrate": "candidate_branch",
    "candidate.accept": "accepted_branch",
}
_LANE_EFFECTS = frozenset(
    {
        "effect:commitment-rebind",
        "effect:git-config",
        "effect:git-merge",
        "effect:git-object-install",
        "effect:git-rebase",
        "effect:git-worktree",
        "effect:git-worktree-index",
        "effect:handoff-package",
        "effect:native",
        "effect:openspec-change-start",
        "effect:openspec-change-start-prepared",
        "lane-resolution:reacquire",
        "observation:git-merge-prepared",
        "observation:native",
    }
)
_REPAIR_RECORDS = frozenset({"effect:commit-signature", "observation:signature-repair-attempt"})
_WINDOW_PREDICATES = frozenset({"lane-resolution:takeover"})


@dataclass(frozen=True)
class LifetimeFacts:
    """Fresh repository facts that can end a lifetime; an absent ref alone never does.

    `pinned` holds commits that something other than a direct ref keeps: fully peeled tags
    and worktree HEADs. `reachable` holds every commit a selected commit reaches, or None when
    that walk could not be observed; a retired lane's records then remain.
    """

    refs: Mapping[str, str]
    pinned: frozenset[str]
    absent_objects: frozenset[str]
    now: datetime
    reachable: frozenset[str] | None = None


def _mapping(value: object, *keys: str) -> Mapping[str, object]:
    for key in keys:
        value = value.get(key) if isinstance(value, Mapping) else None
    return value if isinstance(value, Mapping) else {}


def _text(value: object, *keys: str) -> str:
    *path, last = keys
    found = _mapping(value, *path).get(last)
    return found if isinstance(found, str) and found else ""


def _updates(body: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    updates = _mapping(body, "plan", "effect", "updates")
    return {ref: update for ref, update in updates.items() if isinstance(update, Mapping)}


def _ref_update_lifetime(attestation: Attestation) -> tuple[Lifetime, str]:
    body = attestation.payload.body
    policy = _mapping(body, "plan", "policy")
    transition = policy.get("transition")
    updates = _updates(body)
    lane = ""
    if transition in _LANE_SUBJECT_TRANSITIONS:
        # Absorbed-ref and handoff retirements name the lane as `branch`.
        lane = _text(policy, "subject") or _text(policy, "branch")
    elif transition in _LANE_EXECUTION_TRANSITIONS:
        lane = _text(policy, "execution_branch")
    elif transition in _LANE_REF_TRANSITIONS and len(updates) == 1:
        lane = next(iter(updates)).removeprefix("refs/heads/")
    elif isinstance(transition, str) and transition in _HEAD_BRANCH_FIELDS:
        branch = _text(policy, _HEAD_BRANCH_FIELDS[transition])
        head = _text(updates.get(f"refs/heads/{branch}"), "desired")
        if not head:
            return "open-predicate", attestation.id
        return (
            ("lineage", f"accepted:{head}") if transition == "candidate.accept" else ("head", head)
        )
    elif transition == "release.promote":
        tags = sorted(ref for ref in updates if ref.startswith("refs/tags/"))
        return ("lineage", tags[0]) if len(tags) == 1 else ("open-predicate", attestation.id)
    elif transition == "commit.identity-replace":
        olds = sorted({_text(update, "expected") for update in updates.values()} - {""})
        return (
            ("lineage", f"repair:{' '.join(olds)}") if olds else ("open-predicate", attestation.id)
        )
    return ("operation", lane) if lane else ("open-predicate", attestation.id)


def _lane_branch(attestation: Attestation) -> str:
    body = attestation.payload.body
    for holder in ("observation", "freshness", "claim"):
        if branch := _text(body, holder, "branch"):
            return branch
    if branch := _text(body, "branch"):
        return branch
    subject = attestation.subject
    return subject.removeprefix("git:branch:") if subject.startswith("git:branch:") else ""


def _commit_subject(attestation: Attestation) -> str:
    subject = attestation.subject
    return subject.removeprefix("git:commit:") if subject.startswith("git:commit:") else ""


def _prefixed(prefix: str, value: str) -> str:
    return f"{prefix}{value}" if value else ""


def _repair_old(attestation: Attestation) -> str:
    return _prefixed("repair:", _text(attestation.payload.body, "coordinates", "old"))


def _runtime_wheel(attestation: Attestation) -> str:
    return _prefixed("runtime:", _text(attestation.payload.body, "identity", "wheel_sha256"))


_RECORD_HOLDERS: Mapping[str, tuple[Lifetime, Callable[[Attestation], str]]] = {
    "proof:execution": ("head", _commit_subject),
    "publication:remote-effect": ("head", _commit_subject),
    "release:accepted-identity": ("lineage", _runtime_wheel),
    "effect:starter-formation": ("lineage", lambda _item: "repository"),
    **dict.fromkeys(_REPAIR_RECORDS, ("lineage", _repair_old)),
    **dict.fromkeys(_LANE_EFFECTS, ("operation", _lane_branch)),
}


def lifetime(attestation: Attestation) -> tuple[Lifetime, str]:
    """Return the one lifetime of a member and the holder whose evidence can end it."""
    # Only a reader that honours valid_until makes it a lifetime; other windows are prose.
    if attestation.valid_until is not None and attestation.predicate in _WINDOW_PREDICATES:
        return "window", attestation.id
    if attestation.predicate == "effect:git-ref-update":
        return _ref_update_lifetime(attestation)
    kind, holder = _RECORD_HOLDERS.get(attestation.predicate, ("open-predicate", _commit_subject))
    key = holder(attestation) if kind != "open-predicate" else ""
    return (kind, key) if key else ("open-predicate", attestation.id)


def latest_publications(members: Sequence[Attestation]) -> frozenset[str]:
    """Commits that each declared peer's latest publication of each ref selects."""
    latest: dict[tuple[str, str], tuple[datetime, str]] = {}
    for member in members:
        if member.predicate != "publication:remote-effect":
            continue
        targets = _mapping(member.payload.body, "plan", "effect").get("targets")
        for target in targets if isinstance(targets, tuple | list) else ():
            peer = _text(target, "id")
            updates = _mapping({"target": target}, "target").get("updates")
            for update in updates if isinstance(updates, tuple | list) else ():
                key = (peer, _text(update, "target_ref"))
                desired = _text(update, "desired")
                if desired and (key not in latest or latest[key][0] < member.issued_at):
                    latest[key] = (member.issued_at, desired)
    return frozenset(desired for _issued, desired in latest.values())


def _lineage_ended(key: str, facts: LifetimeFacts) -> bool:
    """Only repair lineage ends, once its pre-repair objects are gone.

    Historical accepted bases remain valid maintenance-release inputs, tags may still exist on
    a peer, version admission refuses rollback, and starter formation describes the repository.
    """
    if key.startswith("repair:"):
        return all(old in facts.absent_objects for old in key.removeprefix("repair:").split())
    return False


def _landing(attestation: Attestation) -> tuple[str, str] | None:
    """Select the integration holder of a record already classified as head-lived."""
    if attestation.predicate != "effect:git-ref-update":
        return None
    policy = _mapping(attestation.payload.body, "plan", "policy")
    return _text(policy, "transition"), _text(policy, "candidate_branch")


def _named_commits(attestation: Attestation) -> frozenset[str]:
    """Commits a ref update names as its expected or desired object."""
    return frozenset(
        commit
        for update in _updates(attestation.payload.body).values()
        for commit in (_text(update, "expected"), _text(update, "desired"))
        if commit.strip("0")
    )


def _ended_lanes(
    classified: Sequence[tuple[Attestation, Lifetime, str]], facts: LifetimeFacts
) -> frozenset[str]:
    """Retired lanes whose named commits no selected commit reaches.

    Proof admission and proposal retirement follow a lane's archive and refresh commits only
    while one of them is an ancestor of a selected head, so an unreached lane has no reader.
    """
    if facts.reachable is None:
        return frozenset()
    named: dict[str, set[str]] = {}
    for member, kind, key in classified:
        if kind == "operation":
            named.setdefault(key, set()).update(_named_commits(member))
    return frozenset(
        lane
        for lane, commits in named.items()
        if commits
        and f"refs/heads/{lane}" not in facts.refs
        and commits.isdisjoint(facts.reachable)
    )


@dataclass(frozen=True)
class _Evidence:
    """Positive evidence gathered once from all members before each member is judged."""

    landed: Mapping[tuple[str, str], datetime]
    selected: frozenset[str]
    ended_lanes: frozenset[str]


def _evidence(
    classified: Sequence[tuple[Attestation, Lifetime, str]], facts: LifetimeFacts
) -> _Evidence:
    landed: dict[tuple[str, str], datetime] = {}
    for member, kind, _key in classified:
        if kind == "head" and (landing := _landing(member)):
            landed[landing] = max(landed.get(landing, member.issued_at), member.issued_at)
    publications = latest_publications([member for member, _kind, _key in classified])
    return _Evidence(
        landed=landed,
        selected=frozenset(facts.refs.values()) | facts.pinned | publications,
        ended_lanes=_ended_lanes(classified, facts),
    )


def _has_ended(
    member: Attestation, kind: Lifetime, key: str, facts: LifetimeFacts, evidence: _Evidence
) -> bool:
    if kind == "window":
        return member.valid_until is not None and member.valid_until < facts.now
    # A lane's records end together, never on retirement alone: a reused branch can still
    # select a live lane's start, merge and lease records.
    if kind == "operation":
        return key in evidence.ended_lanes
    if kind == "head":
        # A landing record may precede its ref move; only a later landing supersedes it.
        landing = _landing(member)
        superseded = landing is None or member.issued_at < evidence.landed[landing]
        return bool(facts.refs) and key not in evidence.selected and superseded
    return kind == "lineage" and _lineage_ended(key, facts)


def ended(members: Sequence[Attestation], facts: LifetimeFacts) -> frozenset[str]:
    """Return the identities whose lifetime has ended by evidence in the members and facts."""
    classified = [(member, *lifetime(member)) for member in members]
    evidence = _evidence(classified, facts)
    return frozenset(
        member.id
        for member, kind, key in classified
        if _has_ended(member, kind, key, facts, evidence)
    )
