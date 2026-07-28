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

ETHOS stores host-local runtime state in `.ethos/state/state.sqlite`. The state
store is a projection over current repository facts; it is not a source of
truth, proof evidence, or a substitute for Git, OpenSpec, or tracked records.

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
