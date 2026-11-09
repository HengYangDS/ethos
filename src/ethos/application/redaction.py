"""Redact protected peer identity in a lane's records, and verify a redaction by re-derivation.

The preview needs no key: it lists, for each occurrence in the tracked tree at the lane head, its
file, line and form and whether it lies in the effective roots, and counts the occurrences outside
them; it never returns a value. An apply writes markers and numbers in the effective roots of the
working tree, under the lane's prewrite and an exact head compare. A verify re-derives every marker
and number of a head from its base and records the Attestation `redaction:private-peer`.
"""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import NoReturn

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_patch import unified_patch
from ethos.adapters.repo.peer_feed import local_feed
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.paradigm.peer_identity import Feed
from ethos.repository.paradigm.peer_identity import follow_digests
from ethos.repository.paradigm.peer_identity import generation
from ethos.repository.paradigm.peer_identity import numbering
from ethos.repository.paradigm.peer_identity import read_key
from ethos.repository.paradigm.peer_identity import redact_text
from ethos.repository.paradigm.peer_identity import replacement_spans
from ethos.repository.profile import effective_record_roots
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

PREDICATE = "redaction:private-peer"
_BLOBS = frozenset({b"100644", b"100755"})


def _fail(reason: str) -> NoReturn:
    raise ValueError(reason)


def redact_private_addresses(
    root: Path,
    *,
    apply: bool = False,
    verify: bool = False,
    key: str = "",
    authorize: bool = False,
    expect_head: str = "",
    base: str = "",
    head: str = "",
    rotate: bool = False,
) -> dict[str, object]:
    """Preview, apply or verify one redaction; every gap names a form or a path, never a value.

    Without a known feed every mode answers `unknown` before it validates or uses a key: the
    preview still lists what it reads, and the apply and the verify write and record nothing.
    """
    try:
        known = local_feed(root)
        unknown = {"verdict": "unknown", "state": "feed_unknown", "required_gaps": [*known.gaps]}
        if known.gaps and (apply or verify):
            return unknown
        if verify:
            return _verify(root, known.feed, key=key, base=base, head=head, rotate=rotate)
        if apply:
            return _apply(
                root,
                known.feed,
                key=key,
                authorize=authorize,
                expect_head=expect_head,
                rotate=rotate,
            )
        preview = _preview(root, known.feed)
        return preview | unknown if known.gaps else preview
    except (OSError, ValueError) as error:
        return {"verdict": "block", "state": "blocked", "required_gaps": [str(error)]}


def _preview(root: Path, feed: Feed) -> dict[str, object]:
    head = current_tracked_head(root)
    roots = effective_record_roots(load_repository_profile(root))
    occurrences = _occurrences(_texts(root, head), feed, roots)
    outside = sum(1 for entry in occurrences if not entry["in_roots"])
    return {
        "verdict": "pass",
        "state": "previewed",
        "head": head,
        "roots": list(roots),
        "occurrences": occurrences,
        "count": len(occurrences),
        "outside_roots": outside,
        "required_gaps": [],
    }


def _apply(
    root: Path, feed: Feed, *, key: str, authorize: bool, expect_head: str, rotate: bool
) -> dict[str, object]:
    if not authorize:
        _fail("authorization_required")
    secret = read_key(key)
    head = current_tracked_head(root)
    if expect_head != head:
        _fail("expect_head_mismatch")
    _require_generation(root, secret, rotate=rotate)
    roots = effective_record_roots(load_repository_profile(root))
    texts = _texts(root, head)
    manual = [
        f"peer_occurrence_unclassified:{entry['path']}:{entry['line']}"
        for entry in _occurrences(texts, feed, roots)
        if entry["in_roots"] and entry["form"] == "manual"
    ]
    if manual:
        return {"verdict": "block", "state": "blocked", "head": head, "required_gaps": manual}
    changed = _redacted(texts, feed, secret, roots)
    report: dict[str, object] = {
        "verdict": "pass",
        "head": head,
        "roots": list(roots),
        "changed_paths": sorted(changed),
        "generation": generation(secret),
        "required_gaps": [],
    }
    if not changed:
        return {**report, "state": "unchanged"}
    if any((root / path).read_bytes() != texts[path].encode() for path in changed):
        _fail("redaction_preimage_changed")
    patch = unified_patch((path, texts[path].encode(), changed[path].encode()) for path in changed)
    admission = prewrite_guard(
        root=root,
        paths=[root / path for path in sorted(changed)],
        editor_root=root,
        require_editor_root=True,
        patch=patch,
    )
    if admission["verdict"] != "pass":
        return {
            **report,
            "verdict": admission["verdict"],
            "state": "blocked",
            "required_gaps": admission["required_gaps"],
        }
    if current_tracked_head(root) != head or any(
        (root / path).read_bytes() != texts[path].encode() for path in changed
    ):
        _fail("redaction_preimage_changed")
    applied = run_git(
        root, "apply", "--whitespace=nowarn", "-", stdin=patch.encode(), text=False, check=False
    )
    if applied.returncode or any(
        (root / path).read_bytes() != text.encode() for path, text in changed.items()
    ):
        _fail("redaction_postimage_mismatch")
    return {**report, "state": "redacted"}


def _verify(
    root: Path, feed: Feed, *, key: str, base: str, head: str, rotate: bool
) -> dict[str, object]:
    secret = read_key(key)
    commits = [_commit(root, revision) for revision in (base, head)]
    if not all(commits):
        return {
            "verdict": "unknown",
            "state": "unknown",
            "required_gaps": ["redaction_base_missing"],
        }
    _require_generation(root, secret, rotate=rotate)
    base_commit, head_commit = commits
    roots = effective_record_roots(load_repository_profile(root))
    before, after = _texts(root, base_commit), _texts(root, head_commit)
    expected = {**before, **_redacted(before, feed, secret, roots)}
    differing = sorted(
        path
        for path in {*before, *after}
        if path.startswith(roots) and expected.get(path) != after.get(path)
    )
    if differing:
        gaps = [f"redaction_unverified:{path}" for path in differing]
        return {"verdict": "block", "state": "blocked", "required_gaps": gaps}
    count = sum(1 for entry in _occurrences(before, feed, roots) if entry["in_roots"])
    body = {
        "base": base_commit,
        "head": head_commit,
        "roots": list(roots),
        "count": count,
        "generation": generation(secret),
    }
    recorded = record_attestation_once(root, _attestation(head_commit, body))
    return {
        "verdict": "pass",
        "state": "verified",
        **body,
        "attestation": recorded.id,
        "required_gaps": [],
    }


def _redacted(
    texts: Mapping[str, str], feed: Feed, key: bytes, roots: tuple[str, ...]
) -> dict[str, str]:
    """Return each record in the roots that a redaction changes, digests followed."""
    numbers = numbering(key, feed, "".join(texts.values()))
    changed = {
        path: redacted
        for path, text in texts.items()
        if path.startswith(roots) and (redacted := redact_text(text, feed, key, numbers)) != text
    }
    # A record that holds the digest of a changed file follows it, and so on until none moves;
    # content addresses form no cycle, so more rounds than records means a damaged tree.
    for _round in range(len(texts) + 1):
        renamed = {_digest(texts[path]): _digest(text) for path, text in changed.items()}
        followed = {
            path: moved
            for path, text in texts.items()
            if path.startswith(roots)
            and (moved := follow_digests(changed.get(path, text), renamed))
            != changed.get(path, text)
        }
        if not followed:
            return changed
        changed.update(followed)
    _fail("redaction_digest_cycle")


def _occurrences(
    texts: Mapping[str, str], feed: Feed, roots: tuple[str, ...]
) -> list[dict[str, object]]:
    return [
        {"path": path, "line": number, "form": span.form, "in_roots": path.startswith(roots)}
        for path, text in sorted(texts.items())
        for number, line in enumerate(text.splitlines(), 1)
        for span in replacement_spans(line, feed)
    ]


def _texts(root: Path, revision: str) -> dict[str, str]:
    """Return each regular UTF-8 text blob of a revision's tree; binary content is not read."""
    listing = run_git(root, "ls-tree", "-r", "-z", revision, text=False).stdout
    entries = [
        (meta.split()[2].decode(), name.decode("utf-8", errors="surrogateescape"))
        for record in listing.split(b"\0")
        if record
        for meta, _tab, name in (record.partition(b"\t"),)
        if meta.split()[0] in _BLOBS
    ]
    if not entries:
        return {}
    request = b"".join(f"{oid}\n".encode() for oid, _name in entries)
    stream = run_git(root, "cat-file", "--batch", stdin=request, text=False).stdout
    texts: dict[str, str] = {}
    offset = 0
    for _oid, name in entries:
        header_end = stream.index(b"\n", offset)
        size = int(stream[offset:header_end].split()[2])
        data = stream[header_end + 1 : header_end + 1 + size]
        offset = header_end + 1 + size + 1
        if b"\0" in data:
            continue
        try:
            texts[name] = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return texts


def _commit(root: Path, revision: str) -> str:
    if not revision:
        return ""
    observed = run_git(
        root, "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}", check=False
    )
    return observed.stdout.strip() if observed.returncode == 0 else ""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _require_generation(root: Path, key: bytes, *, rotate: bool) -> None:
    """Refuse a key of another generation than the last recorded one, unless rotating."""
    _set_root, members = read_attestation_set(root)
    recorded = sorted(
        (member for member in members if member.predicate == PREDICATE),
        key=lambda member: member.issued_at,
    )
    last = recorded[-1].payload.body.get("generation") if recorded else None
    if last is not None and last != generation(key) and not rotate:
        _fail("redaction_key_generation_changed")


def _attestation(head: str, body: Mapping[str, object]) -> Attestation:
    issued = datetime.now(UTC)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": PREDICATE,
            "verifier": "ethos",
            "subject": f"{PREDICATE}:{head}",
            "issued_at": issued,
            "valid_from": issued,
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": PREDICATE, "body": dict(body)},
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": None,
            # The verified facts bind the record; it mints no authority.
            "facts_digest": canonical_json_digest(dict(body)),
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
    )
