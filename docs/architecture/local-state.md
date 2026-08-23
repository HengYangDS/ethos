---
subject: ethos:local-state
role: explanation
state: canonical
relations:
  canonical_for: ignored runtime state
---

# Local State

Status: canonical.

Purpose: define the boundary between repository truth and ignored host-local
coordination state.

See also: [Runner And Mutation](runner-and-mutation.md) and
[Command Plane](../reference/command-plane.md).

ETHOS stores host-local runtime state under `<git-common-dir>/ethos/`, shared by
every linked worktree without materializing files in any checkout. The current
database is `<git-common-dir>/ethos/state.sqlite`; content-addressed local proof
receipts are under `<git-common-dir>/ethos/attestations/`. This state is a
projection over current repository facts, not a source of truth or a substitute
for Git, OpenSpec, or tracked records.

Tracked `.ethos/` paths are repository declarations, never mutable runtime
storage. All state readers and writers resolve the same Git-common owner; a
linked worktree cannot introduce a parallel state authority.

Use the public reader to inspect the current repository boundary:

```bash
ethos status --json
```

A status result reports each Work Lane Lease as exactly `valid`, `expired`,
`unknown`, or `missing`. `unknown` means a row exists but its wire is malformed,
retired, mismatched, or otherwise unverifiable; it is never treated as missing
and is observe-only. These facts guide the next action but do not authorize a
write, renewal, handoff, retirement, repair, or cleanup.

Every valid Lease carries one immutable `base_commitment_digest`. The
current release admits no amendment set, so the selected Commitment digest
used by prewrite, TransitionPlan, proof, handoff, head advance, and closeout must equal
that base digest exactly. The SQLite row duplicates only its indexed identity,
owner, subject, and expiry fields; every replacement is a complete exact-CAS
reissue of the strict Lease wire.

Tool caches belong under ignored runtime locations. Curated evidence becomes
repository truth only after its owning gate promotes it through the declared
evidence path.
