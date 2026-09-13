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

Immutable hook runtimes and generated launchers are also common-dir projections:
`<git-common-dir>/ethos/runtime/<digest>/` and
`<git-common-dir>/ethos/hooks/<digest>/`. Repository-common Git config owns the
single effective `core.hooksPath` and `gc.packRefs=false` activation. Linked
worktrees inherit that activation; worktree-local values for those keys are
invalid parallel owners and `ethos hook install` removes them.

After activation, the runtime retirement owner retains the selected runtime and
hook generation, effective repository-config references, live process-command
references and linked `.venv` interpreter bindings. An operation or diagnostic
record naming a former generation is historical observation, not a dependency
on that executable; recovery uses the current selected runtime. Retirement
neither edits nor deletes those records.

Each removal re-observes dependencies and the exact generated directory under
the bounded native selector lock. Unknown observations, contention or stale
coordinates defer reclamation without denying a completed activation. Partial
results preserve actual removed, retained and deferred paths; the public install
command can derive a fresh retry. This observation boundary does not claim
complete fd/mmap coverage, same-UID isolation or strong-kill orphan scavenging.

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

Every Lease row contains exactly `lane_ref`, `holder_ref`, `generation`, and
`expires_at`. It coordinates one actor-lane relationship and contains no Git
HEAD, tree, index, worktree, OpenSpec identity, Commitment, path scope,
handoff state, or effect outcome. Commands compile those values from fresh
Facts and exact intent, then compare-and-swap only the four-field relation when
ownership changes.

Tool caches belong under ignored runtime locations. Curated evidence becomes
repository truth only after its owning gate promotes it through the declared
evidence path.
