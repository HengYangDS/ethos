## Context

The existing exceptional command deliberately couples exact native lease
relinquishment with compare-and-delete of one unbound ref. A historical failed
transaction can nevertheless leave a visible partial state: the ref is absent,
the recorded source worktree is absent, and the exact foreign lease remains.
The historical attempt is immutable evidence, but its accepted-head and policy
bytes are historical facts; the later reconciliation must be controlled by the
current accepted policy without rewriting history.

## Goals / Non-Goals

**Goals:**

- Reconcile only the exact surviving lease generation after current policy,
  current protected refs, current claim/Chronicle bytes, source-path absence,
  and immutable prior attempt all agree.
- Retain a no-clobber attempt/receipt chain that distinguishes the historical
  ref deletion from the later native lease-only CAS.
- Keep the public transition nested under Work Lane retirement and vendor
  neutral.

**Non-Goals:**

- Recreate, delete, or force-update a source ref; hand off or impersonate the
  unavailable holder; modify a remote; clean another lane; or repair the
  historical attempt record.

## Decisions

1. **Use a distinct `reconcile-ref-absent` command.** The normal unbound command
   correctly requires a present accepted-ancestor ref, so overloading it would
   obscure which effect is being reconciled. The new command can revoke only a
   lease and explicitly represents ref absence.

2. **Bind prior and current evidence separately.** The current Chronicle binds
   the historical attempt’s operation ID, historical accepted head, claim, and
   Chronicle digests. Admission reads the attempt from the current accepted
   control store but compares those historical fields exactly; it does not
   require the current accepted head to equal the old one.

3. **Publish a new no-clobber record pair.** Before CAS, write a reconciliation
   attempt containing the full validated source attempt. After CAS, write a
   receipt with ref/worktree/lease/protected-ref/Chronicle postconditions. This
   makes the later repair auditable without relabeling the historical raw effect
   as a successful native retirement.

4. **Use same-value protected-ref CAS operations in the ordinary delete
   transaction.** They preserve exact protected-ref values while allowing the
   reference-transaction hook to admit the complete atomic transaction.

## Risks / Trade-offs

- **Current policy drifts after historical attempt** → require accepted
  Chronicle/Claim byte identity and re-observation immediately before CAS.
- **Lease or source path is reused** → bind source lease ID, holder, epoch,
  expected head, and recorded path digest; block on any mismatch.
- **Receipt publication fails after CAS** → surface an explicit local residue;
  never claim reconciliation complete without the receipt.
- **Command becomes a generic takeover surface** → require different non-empty
  actor plus user-confirmed controls and exact target-specific Chronicle fields.

## Migration Plan

1. Land the code, tests, command reference, canonical deltas, claim, and
   Chronicle via the normal Work Lane lifecycle.
2. After acceptance, re-observe the one target and perform dry-run, then apply
   only if all bindings are current.
3. On any gap, retain the residue and records unchanged. There is no rollback
   that recreates a deleted ref or revoked foreign lease.
