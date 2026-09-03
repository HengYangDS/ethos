## Context

Linked-lane retirement spans three independently durable carriers: a Git
worktree registration and directory, a branch ref, and a SQLite Lease. The
retired abandonment implementation performed those effects sequentially while
using the target worktree as the subprocess working directory. Removing that
worktree invalidated the execution coordinate needed by the next Git command.
Its recovery path then compared current state with the original all-present
prestate, so the exact partial state it created was rejected as drift.

The current retirement package already establishes a surviving accepted
`control_root`, exact Git ref effects, Lease fencing, and native post-observation.
This Change extends that sole owner rather than restoring the independent
abandonment implementation.

## Goals / Non-Goals

**Goals:**

- model retirement as an immutable request plus a pure reduction of observed
  carrier states;
- preflight all execution coordinates before destructive effects;
- persist progress after every effect and recover from native facts if a crash
  occurs between an effect and its checkpoint;
- expose one public recovery command for all partial linked retirements;
- restore explicit clean divergent-lane abandonment without a parallel engine;
- preserve exact holder and foreign-owner protections.

**Non-Goals:**

- compatibility with historical abandonment receipt schemas;
- automatic semantic judgment for dirty or ambiguous lanes;
- raw Git or SQLite recovery guidance;
- changes to AIGW or Proxy.

## Decisions

### One immutable operation contract

The retirement owner compiles a frozen request containing repository common
directory, surviving control root, mode, branch, HEAD, tree, accepted
coordinates, worktree coordinates, Lease observation, actor authority, reason,
and ordered effects. Its content digest names the request. Progress snapshots
are immutable observations that reference that request digest; they are not a
second authority and cannot change the requested terminal state.

### Pure carrier-state reduction

The reducer maps fresh native observations to this monotonic state:

```text
observed -> preflighted -> worktree_removed -> ref_removed -> lease_revoked -> terminal
```

`completed_effects` and `remaining_effects` are derived only from observed
carrier postconditions. Process-local booleans are never authoritative. A crash
after a carrier effect therefore cannot lose progress: recovery loads the
immutable request and derives the next effect from current facts.

### Surviving control root owns every Git process

Every Git observation and mutation after target selection runs from the
preflighted accepted control root. The target worktree path is data, never the
working directory for a later subprocess. Preflight resolves the Git executable
and proves the control root remains usable before any deletion.

### Forward-only recovery

The operation converges toward absence in the order worktree, ref, Lease.
Recovery does not recreate a deleted worktree or ref. This removes compensation
cycles and preserves the user's authorized destructive intent. Lease revocation
is last so a partial operation retains ownership fencing until Git reaches its
terminal state.

### One public recovery route

`ethos lane retire recover --receipt ... --receipt-sha256 ...` validates current
receipt bytes and repository identity, re-observes all carriers, checks the
original authority, and either reports the remaining effects or applies them.
Every partial result emits this exact command. Repeating it after completion is
an idempotent recognition.

### Abandonment is a retirement mode, not a subsystem

`ethos lane retire abandon` derives the same operation contract with a
structured abandonment reason and the existing owner/maintainer authorization
rules. Apply and recovery use the common reducer and executor. No old receipt
reader, wrapper, or standalone mutation module is retained.

## Risks / Trade-offs

- **Crash between effect and progress write:** recovery derives progress from
  native carriers, so the snapshot is evidence but not the source of truth.
- **Ref moves after worktree deletion:** exact request observations classify
  this as ambiguous drift and block; Lease remains intact.
- **Git executable disappears after preflight:** the result is partial and the
  surviving control root allows a later recovery after runtime repair.
- **Forward-only semantics remove compensation:** this is deliberate for an
  explicitly authorized retirement; keeping the Lease until Git completion
  preserves the remaining safety boundary.

## Migration Plan

1. Specify and validate the terminal operation contract.
2. Add failing reducer, partial-effect, recovery, CLI, and real-Git tests.
3. Implement the immutable request, observation reducer, progress store, and
   bounded executor in the current retirement package.
4. Route linked retirement and abandonment through that owner and expose the
   single recovery command.
5. Prove, archive, land, close out, and activate a package-only runtime before
   reporting delivery.
