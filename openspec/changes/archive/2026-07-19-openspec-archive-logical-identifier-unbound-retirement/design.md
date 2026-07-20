## Context

ETHOS native exceptional retirement is intentionally fail-closed: it requires
an accepted, byte-identical Chronicle and Claim naming one exact unbound
accepted-ancestor ref/head. The original archive-reader Chronicle is accepted
but records product work rather than this later lifecycle effect.

## Goals / Non-Goals

**Goals:**

- Bind exactly `work/openspec-archive-logical-identifier-20260719` at
  `8cd3d3b03e6f0991bf7b5b778ed34dfe7bb61ade`.
- Preserve native holder/lease CAS, ref compare-and-delete, and receipt-based
  postconditions as the sole destructive mechanism.
- Keep this carrier neutral to vendors, accounts, sessions, and host paths.

**Non-Goals:**

- Delete a ref or revoke a lease through this authoring carrier.
- Generalize to a batch inventory, act on a foreign residue, or mutate a remote
  or hosted system.

## Decisions

1. **Use a separate Claim and Chronicle.** Historical product evidence remains
   immutable; target-specific retirement evidence is not inferred from it.
2. **Bind the original immutable source head.** Current effect-time admission
   still reobserves that head, accepted bytes, lease generation, worktree state,
   and protected refs.
3. **Leave effect authority in the native command.** Acceptance authorizes only
   a later exact command; it does not itself remove source operational state.

## Risks / Trade-offs

- **Target or policy drift** → native admission blocks and preserves the ref.
- **Current holder or lease generation mismatch** → the native CAS refuses to
  relinquish the lease.
- **Candidate movement during carrier lifecycle** → refresh the owned lane,
  regenerate required evidence, and reprove before land.
