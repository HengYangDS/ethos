"""Report whether a history rebuild could apply, by count and fixed gap, writing nothing.

Readiness and the apply are the only readers of the key. Readiness binds the record to its
originals, walking every declared ref once, reads every declared peer through the one namespace
listing and computes in memory the rebuilt tag messages it must judge. It reports each entry's
discovered count and each retained prefix's occurrence total by index, the quotes of rewritten
objects by kind and each peer's review heads, and it refuses what an apply could not carry: an
undeclared span, feed value or local ref, an item in a header or a tree entry name, a ref or a peer
in another state, a disposition the ref cannot take, a `keep` or a `retag` that could not publish,
and history that the walk cannot see. It records nothing, not even an observed absence, and its
report names refs, lists and indices, never a value; a Git failure reports its fixed code alone.
"""

from __future__ import annotations

from os.path import relpath
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.commit.rebuild.binding import bind
from ethos.adapters.repo.commit.rebuild.discovery import discovered_gaps
from ethos.adapters.repo.commit.rebuild.discovery import quoted_ids
from ethos.adapters.repo.commit.rebuild.discovery import transformed
from ethos.adapters.repo.commit.rebuild.entries import retained_totals
from ethos.adapters.repo.commit.rebuild.peers import peer_states
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.peer_feed import local_feed
from ethos.adapters.repo.release import release_provenance
from ethos.adapters.repo.release import release_qualification
from ethos.adapters.repo.worktree_list import raw_worktree_records
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.outcome import outcome_of
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.peer_identity import counts
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.rebuild_record import ENTRY_KINDS
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_ref_role
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import publication_transport_tags
from ethos.repository.release.publication import topology_remotes

if TYPE_CHECKING:
    from collections.abc import Collection
    from collections.abc import Iterator

    from ethos.adapters.repo.commit.rebuild.binding import Binding
    from ethos.contracts.branch.roles import BranchRolePolicy

_REWRITTEN = frozenset({"rebuild", "retag"})
# The dispositions each kind of ref admits; any other ref can only retire.
_ADMITTED = (
    ("refs/heads/", {"rebuild", "retire", "keep"}),
    ("refs/tags/", {"retag", "retire", "keep"}),
)
# The refs a linked worktree holds alone, which the main worktree's ref listing never shows.
_PRIVATE = ("refs/worktree/", "refs/bisect/", "refs/rewritten/")


def rebuild_readiness(root: Path, *, record: str, key: str) -> dict[str, object]:
    """Report the readiness of the rebuild that the record at `record` authorizes.

    The record is read at the accepted head, given from the repository root or absolutely.
    """
    path = Path(record)
    relative = Path(relpath(path.resolve(), root.resolve())) if path.is_absolute() else path
    try:
        secret = read_key(key)
        policy = load_branch_role_policy(root)
        accepted = f"refs/heads/{policy.accepted_branch}"
        old = run_git(root, "rev-parse", "--verify", accepted).stdout.strip()
        bound = bind(root, path=relative.as_posix(), old=old, key=secret)
        return _report(root, relative.as_posix(), secret, bound, policy=policy, old=old)
    except ProcessExecutionError as error:
        gaps: tuple[str, ...] = (error.code,)
    except ValueError as error:
        gaps = outcome_of(error).gaps
    return {"verdict": "block", "state": "blocked", "required_gaps": list(gaps), "next_action": ""}


def _report(
    root: Path, path: str, key: bytes, bound: Binding, *, policy: BranchRolePolicy, old: str
) -> dict[str, object]:
    config = release_config(root)
    known = local_feed(root)
    remotes = topology_remotes(publication_topology(root, config))
    peer_gaps, reviews = peer_states(
        root, bound.record, olds=bound.olds, key=key, remotes=remotes, affected=bound.affected
    )
    declared = {image for item in bound.resolved for image in item.images}
    discovered = discovered_gaps(bound.history, bound.feed, declared, known.feed)
    rewritten, walked = _rewritten(bound)
    quotes, ambiguous = quoted_ids(bound.history, rewritten, path)
    gaps = [
        *bound.gaps,
        *known.gaps,
        *_ref_gaps(root, bound, policy, remotes),
        *_disposition_gaps(bound, policy, config),
        *peer_gaps,
        *sorted(discovered),
        *(["rebuild_quote_ambiguous"] if ambiguous else []),
        *_retag_gaps(root, bound, key, walked),
        *_hidden_gaps(root),
    ]
    found = counts(bound.found)
    listed = {kind: [None] * len(getattr(bound.record.transform, kind)) for kind in ENTRY_KINDS}
    for item in bound.resolved:
        listed[item.kind][item.index] = sum(found.get(image, 0) for image in item.images)
    texts = [sighting.text for sighting in bound.history.sightings]
    return {
        "verdict": "block" if gaps else "pass",
        "state": "blocked" if gaps else "ready_to_rebuild",
        "head": old,
        "counts": {kind: values for kind, values in listed.items() if values},
        "retained": retained_totals(bound.record.transform.retain, bound.feed, texts),
        "quoted_ids": quotes,
        "discovered": dict(sorted(discovered.items())),
        "review_refs": reviews,
        "required_gaps": list(dict.fromkeys(gaps)),
        "next_action": "",
    }


def _rewritten(bound: Binding) -> tuple[dict[str, str], set[str]]:
    """Return what a `rebuild` or `retag` ref reaches that is affected, and all it reaches."""
    links, commits = bound.history.links, set(bound.history.commits)
    pending = [
        bound.olds[ref]
        for ref, item in bound.record.refs.items()
        if item.disposition in _REWRITTEN and ref in bound.olds
    ]
    walked: set[str] = set()
    while pending:
        oid = pending.pop()
        if oid not in walked:
            walked.add(oid)
            pending.extend(links.get(oid, ())[1:] if oid in commits else links.get(oid, ())[:1])
    kinds = {oid: "commit" if oid in commits else "tag" for oid in walked & bound.affected}
    return kinds, walked


def _ref_gaps(
    root: Path, bound: Binding, policy: BranchRolePolicy, remotes: dict[str, str]
) -> Iterator[str]:
    """Every local ref is declared or allowlisted, holds its declared value, and main is dev."""
    record = bound.record
    rows = run_git(root, "for-each-ref", "--format=%(refname) %(objectname) %(symref)").stdout
    local = {
        ref: (oid, target) for ref, oid, *target in (row.split(" ") for row in rows.splitlines())
    }
    tracked = {
        f"refs/remotes/{remote}/{ref.removeprefix('refs/heads/')}"
        for remote in remotes.values()
        for ref in record.refs
        if ref.startswith("refs/heads/")
    } | {
        f"refs/remotes/{remotes[peer]}/tags/{ref.removeprefix('refs/tags/')}"
        for ref, item in record.refs.items()
        for peer, state in item.peers.items()
        if ref.startswith("refs/tags/") and peer in remotes and state not in {"old", "absent"}
    }
    rebuilt = f"refs/ethos/rebuild/{record.id}/rebuilt/"
    for ref, (_oid, target) in local.items():
        head = (
            ref.startswith("refs/remotes/")
            and ref.endswith("/HEAD")
            and target[:1]
            and target[0] in tracked
        )
        if (
            ref not in record.refs
            and ref not in tracked
            and ref != ATTESTATION_SET_REF
            and not ref.startswith(rebuilt)
            and not head
        ):
            yield f"rebuild_ref_undeclared:{ref}"
    yield from (
        f"rebuild_ref_state:{ref}"
        for ref in record.refs
        if ref in bound.olds and local.get(ref, ("", ()))[0] != bound.olds[ref]
    )
    accepted, released = (
        local.get(f"refs/heads/{name}", ("", ()))[0]
        for name in (policy.accepted_branch, policy.release_branch)
    )
    if accepted != released:
        yield "rebuild_main_not_dev"


def _disposition_gaps(
    bound: Binding, policy: BranchRolePolicy, config: dict[str, Any]
) -> Iterator[str]:
    """A ref takes only the dispositions its kind admits; a kept ref is unaffected and published.

    A branch rebuilds, an annotated tag re-tags and any ref retires; a ref outside branches and
    tags can only retire, and ETHOS publishes no lightweight tag.
    """
    tags = tuple(config.get("protected_refs", {}).get("tags", ()))
    transport = publication_transport_tags(config)
    commits = set(bound.history.commits)
    for ref, item in bound.record.refs.items():
        oid = bound.olds.get(ref, "")
        annotated = oid in bound.history.headers and oid not in commits
        if not _admits(ref, item.disposition, annotated=annotated):
            yield f"rebuild_disposition_refused:{ref}"
        if item.disposition == "keep":
            lightweight = ref.startswith("refs/tags/") and not annotated
            published = publication_ref_role(policy, ref, tags, transport)[2] and not lightweight
            yield from _kept(ref, affected=oid in bound.affected, published=published)
        if item.disposition == "retag" and annotated:
            yield from _retagged(ref, bound.history.links[oid][0], bound.affected, commits)


def _admits(ref: str, disposition: str, *, annotated: bool) -> bool:
    """Whether the ref's kind admits the disposition; a re-tag needs an annotated tag."""
    admitted = next((kinds for head, kinds in _ADMITTED if ref.startswith(head)), {"retire"})
    return disposition in admitted and (disposition != "retag" or annotated)


def _kept(ref: str, *, affected: bool, published: bool) -> Iterator[str]:
    """A kept ref reaches no declared item, and ETHOS can publish it."""
    if affected:
        yield f"rebuild_keep_affected:{ref}"
    if not published:
        yield f"rebuild_keep_unpublishable:{ref}"


def _retagged(
    ref: str, target: str, affected: Collection[str], commits: Collection[str]
) -> Iterator[str]:
    """A re-tag re-creates one level on an affected commit, so it points to `retire` otherwise."""
    if target not in commits:
        yield f"rebuild_retag_of_tag:{ref}:retire"
    elif target not in affected:
        yield f"rebuild_retag_target_unaffected:{ref}:retire"


def _retag_gaps(root: Path, bound: Binding, key: bytes, walked: set[str]) -> Iterator[str]:
    """A re-tag publishes on its original release record and qualification, never re-judged.

    The message the rebuild prepares for it may name no private address, and a message that the
    transform refuses is never judged, so it refuses too.
    """
    paradigm = load_repository_paradigm()
    messages = {sighting.oid: sighting for sighting in bound.history.sightings if not sighting.path}
    commits = set(bound.history.commits)
    for ref, item in bound.record.refs.items():
        oid = bound.olds.get(ref, "")
        if item.disposition != "retag" or oid in commits or oid not in messages:
            continue
        target = oid
        while target in bound.history.headers and target not in commits:
            target = bound.history.links[target][0]
        yield from _released(root, ref, oid, target, walked)
        text = transformed(messages[oid], bound.feed, key)
        if text is None:
            yield f"rebuild_tag_message_untransformable:{ref}"
        elif paradigm.names_private_address(text):
            yield f"rebuild_tag_message_private:{ref}"


def _released(root: Path, ref: str, oid: str, target: str, walked: set[str]) -> Iterator[str]:
    """The original tag's release record qualifies its target, and maps a maintenance base.

    Its qualification is the proof that record embeds for its own commit; today's CHANGELOG grammar
    is never read.
    """
    try:
        plan = release_provenance(root, ref=ref, oid=oid)
    except ValueError:
        plan = None
    if plan is None:
        yield f"rebuild_retag_unreleased:{ref}"
        return
    base = str(plan.facts.get("values", {}).get("release_request", {}).get("base") or "")
    if base and base not in walked:
        yield f"rebuild_retag_base_unmapped:{ref}"
    proof = release_qualification(plan)["proof_attestation_id"]
    if plan.facts.get("head") != target or not proof:
        yield f"rebuild_retag_unqualified:{ref}"


def _hidden_gaps(root: Path) -> Iterator[str]:
    """History the walk cannot see: a shallow or grafted store, or a linked worktree's own refs."""
    if run_git(root, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        yield "rebuild_history_hidden:shallow"
    common = run_git(root, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    if (Path(common.strip()) / "info" / "grafts").exists():
        yield "rebuild_history_hidden:grafts"
    for record in raw_worktree_records(root)[1:]:
        tree = Path(record["worktree"])
        private = (
            run_git(tree, "for-each-ref", "--format=%(refname)", *_PRIVATE, check=False)
            if tree.is_dir()
            else None
        )
        if "detached" in record or private is None or private.returncode or private.stdout.strip():
            yield "rebuild_history_hidden:worktree"
