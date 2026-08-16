# Design

## Authority

`create_git_commit` remains the only owner of direct `git commit-tree` object
creation. It reads effective `commit.gpgsign`; when enabled it binds the
configured SSH signer, creates with `-S`, and immediately verifies the result
against the existing repository-external trust anchor. A failed creation or
verification returns a failed process before any caller can mutate a ref.

## Suffix repair

`lane repair-identity` retains its current exact single-commit path. Its new
suffix derive path observes one clean owned Work Lane, a valid bound Lease, the
configured integration train, and an explicit exclusive suffix base. It accepts
only a linear first-parent suffix containing the current Work Lane HEAD and the
current candidate/accepted/release heads. It recreates each commit in order with
the original tree, message, author and committer metadata, while replacing the
parent with the preceding recreated commit and applying current signing policy.

The derive result persists one immutable content-addressed receipt containing
the old base/head, every old/new commit mapping and payload observation, the
complete old/new ref map, Lease generation, tree and actor. Dry-run and apply
consume that receipt and re-observe every coordinate. Apply performs one
Git-effect CAS over all affected refs, synchronizes linked worktrees, then
advances the existing Lease to the mapped Work Lane HEAD. An identical retry
recognizes already-applied refs and completes remaining worktree/Lease
projection; drift outside the receipt fails closed.

## Safety boundary

Suffix repair is not a general rebase or content rewrite. Every recreated
commit must preserve its original tree, message, author identity/date, and
committer identity/date; only signature headers and parent OIDs may differ.
Every new commit must pass external signature verification. Merge commits,
missing train heads, dirty worktrees, foreign actors, stale Leases, and any
unobserved ref movement block before mutation. Existing proof remains bound to
the old HEAD and therefore is not reused as proof of the rewritten HEAD; the
caller must run a new exact-HEAD proof after repair.
