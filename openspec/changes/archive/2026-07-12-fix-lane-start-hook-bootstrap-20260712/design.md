## Context

The reference-transaction hook protects raw accepted-root ref movement and
updates an existing Work Lane lease after a normal Work Lane ref move.  Git also
reasserts a newly created Work Lane ref while `git worktree add -b` initializes
the checkout.  That reassertion has identical old and new object IDs, occurs
before `ethos lane start` can create a lease, and does not need a Python
admission decision.

The hook currently invokes its runtime adapter before it distinguishes this
case.  A fresh checkout lacks its checkout-local interpreter, so the adapter
starts `uv` in an isolated nested cache.  That work is unnecessary for an
unchanged non-accepted ref and can wait on package acquisition when the network
is unavailable.

## Goals / Non-Goals

**Goals:**

- Allow fresh Work Lane creation to complete without a local runtime or network.
- Preserve fail-closed accepted-root admission.
- Preserve Python-based Work Lane lease-head repair for an actual Work Lane head
  transition.

**Non-Goals:**

- Do not weaken candidate or accepted ref proof admission.
- Do not alter the runtime-bootstrap cache design or use a shared source
  environment across worktrees.
- Do not change lease authority, expiry, or retirement semantics.

## Decisions

1. **Skip only fresh `work/*` setup events with no executable local runtime.**
   The hook will continue before invoking the runtime adapter when a Work Lane
   ref is created from Git's zero OID or reasserted with identical OIDs, and the
   selected checkout-local interpreter is absent.  These events occur before a
   new Work Lane has a lease, so they cannot repair a lease head or advance a
   protected root.

   Skipping every non-accepted ref without a runtime was rejected: a candidate
   transition must retain its existing proof admission, and a real Work Lane
   commit must still reach the Python transition logic that maintains its lease
   head.  Changing the nested cache policy was also rejected: it would retain a
   needless dependency installation in a Git setup hook and would not establish
   that the ref is a setup event.

2. **Leave all other hook paths unchanged.**  Accepted refs still invoke the
   existing guard even if their runtime is missing, preserving fail-closed
   behavior.  A changed Work Lane ref continues to invoke the existing command
   and its committed-phase lease repair.

## Risks / Trade-offs

- [Git emits a different setup transaction shape] → The guard is deliberately
  narrow and only applies to equal old/new OIDs; a changed ref keeps current
  admission behavior.
- [A future hook edit broadens the bypass] → A regression test asserts the
  branch, OID-equality, and runtime-absence predicates together.

## Migration Plan

1. Add the narrow shell guard and regression test.
2. Run the focused hook test, strict OpenSpec validation, and the normal
   HEAD-bound proof before landing.
3. If a regression appears, remove the guard; no persistent data migration is
   involved.

## Open Questions

None.
