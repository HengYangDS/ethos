# Design

## Context

`peer_feed` builds the feed from the protected peers among the publication declaration's remotes:
a peer is protected when a URL of its remote names a private-class host or its `forgePrivate` is
true. Git reads a remote that holds only forge keys as a URL equal to its own name, so
`git remote get-url` cannot tell a remote without a URL from one with a hostless URL, and a declared
peer without any remote is silently left out. The four readers of the feed, the push check and the
three redaction modes, treat an empty feed as nothing found, and `status` stays quiet about it.

## Goals / Non-Goals

Goals: make every reader of the local feed refuse to judge a feed the clone cannot know, and make
`required` refuse it.

Non-Goals: the GitLab job's backstop, whose feed is the job's own identity and which stays inert
outside such a job; how a literal is found; the advertisement; the disabled mode; `status`.

## Decisions

1. **The feed reader owns its completeness.** `peer_feed.py` reads the publication declaration,
   every remote's forge and URL keys in one `git config` read, and the URLs Git rewrites, and
   returns the feed with its gaps as one value, whose feed alone answers whether anything is fed. A
   declared peer is unread when its remote holds no URL in its `url` or `pushurl` keys, read as Git
   reads them, where an empty value clears the earlier ones; a URL counts as read whatever its host,
   so a local path or a `file:` URL is read and protected only through `forgePrivate`. The gaps are
   the declaration's own required gaps when it is invalid, which name its repair; else
   `peer_identity_feed_unreadable:<remote>` for each unread declared peer in declaration order; else
   `peer_identity_feed_empty` when nothing is fed; else none. An unread peer comes before an empty
   feed because the unread remote may be the protected one, and adding it is the repair.
2. **A remote marked private feeds wherever it is declared.** A remote with `forgePrivate` true
   that the publication declaration does not name feeds its URLs and forge keys like a declared
   peer, because its owner declared it private. It is never unread: only a declared peer is
   expected to have a remote. `status` therefore names such a remote under `disabled` as it names a
   protected declared peer.
3. **`required` refuses an unknown feed.** Push admission reads the mode first, as now; a deletion
   returns before it as now, and under `required` the feed gaps return before any advertisement is
   read, whichever peer the push targets. The decision reason `peer_identity_literal_refused`
   becomes `peer_identity_refused` for every peer identity gap, because an unreadable range and an
   unknown feed are not literals. An invalid declaration already blocks the push through its ref
   admission, whose reason `publication_ref_unavailable` comes first, so `peer_identity_refused`
   names a push that only peer identity gaps block.
4. **The redaction verb answers `unknown` in every mode.** It reads the feed once per call, before
   authorization and the key, whatever the mode: the verb is an explicit operation, not a guard
   that the profile turns on. With feed gaps the preview keeps its occurrence list and answers
   `unknown` with the gaps; it stays unenforced, so its exit is 0 and a reader judges its verdict.
   The apply and the verify answer `unknown` with the gaps, write nothing and record no
   Attestation, and exit as any unknown does. The CLI reads standard input before the verb runs,
   so the verb neither validates nor uses a key it read.
5. **`status` keeps its rules.** It reads only whether anything is fed, so it adds no feed gap: a
   hosted job's clone holds no declared peer's remote, and such an advisory would sit in every
   hosted run of a `required` repository, while the push refusal names the repair exactly when a
   push needs it.

## Alternatives

- **Advise in `status`.** Rejected for the reason of decision 5.
- **Refuse only an empty feed.** Rejected: a second protected peer, or a peer marked `forgePrivate`
  whose remote has no URL, would still leave a partial feed, which the push-check design promised
  to refuse.
- **Declare protection in tracked files.** Rejected: whether a peer is protected follows from its
  local identity, which tracked files must not hold.

## Risks / Trade-offs

- Every clone that pushes under `required` needs a remote for each declared peer, so a working
  clone of one peer adds the other's remote before it pushes; the refusal names the remote.
- An undeclared remote marked `forgePrivate` but holding no URL feeds only its forge keys.
- An undeclared or stale remote marked `forgePrivate` widens the feed: a push that adds its host,
  even one it shares with the public peer, refuses under `required`. The refusal errs toward
  privacy, and unsetting the mark is the repair.
