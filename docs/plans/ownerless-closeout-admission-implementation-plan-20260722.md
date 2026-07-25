---
subject: ethos:ownerless-closeout-admission-implementation-plan-20260722
role: plan
state: archived
relations:
  implements: ownerless-closeout-admission-design-20260722
  superseded_by: native-lane-resolution-authority-implementation-plan-20260724
---

# Ownerless Closeout Admission Implementation Plan

Status: archived on 2026-07-25. This historical plan is fully superseded by
[Native Lane Resolution Authority](native-lane-resolution-authority-implementation-plan-20260724.md)
and contains no executable current guidance.

## Historical delivery sequence

The original 2026-07-22 plan separated four concerns:

1. create canonical date-bound Work Lane branch and sibling-worktree identities;
2. admit a clean ownerless accepted ancestor without synthesizing ownership;
3. run the admission immediately before a no-force worktree removal and exact
   ref compare-and-swap;
4. seal the transition with immutable evidence and retire only the exact
   implementation lane after normal lifecycle proof.

It required fail-closed rejection for dirty or diverged targets, valid leases or
Claims, stale decisions or Chronicles, path and HEAD drift, malformed records,
competing reservations, failed postconditions, and uncertain partial effects.

## Delivery-state update — 2026-07-23

By 2026-07-23, the provider-specific admission route had been deployed and the
candidate baseline already contained its bounded adapter, fence, reservation,
receipt, recovery, and no-force compare-and-swap behavior. That update narrowed
the remaining lane-owned work to canonical lane identity at creation time. The
separate provider deployment and adapter-integration tasks were declared
superseded rather than reimplemented in this plan. This chronology records the
scope change only; it does not preserve the retired command, schema, source path,
or deployment instructions as current guidance.

## Why the implementation route was retired

The plan assigned pre-effect admission to an out-of-process provider-specific
verifier and proposed a subprocess adapter plus separate deployment checks. That
route made ETHOS depend on an unrelated product for facts ETHOS already had to
re-observe before effect. It also duplicated contract and recovery semantics and
could not serve as the sole owner of retry, completed-effect recovery, and
cleanup.

The provider-specific source path, command surface, flags, response schema,
adapter shape, deployment instructions, and regression fixtures are deliberately
absent from current tracked guidance. Git history and immutable local historical
records remain untouched.

## Retained implementation invariants

The successor implementation keeps only the product-native invariants:

- one immutable decision and Chronicle snapshot;
- exact configured Work Lane role, Git ref, worktree registration and
  incarnation, accepted ancestry, lease, Claim, holder, and record observation;
- one exact SQLite target fence and one typed durable reservation;
- complete under-fence re-observation before any Git or worktree effect;
- no-force worktree removal and accepted-ref-bound exact target-ref CAS;
- explicit three-state postconditions;
- one immutable provider-neutral completion receipt;
- completed-effect recovery before ordinary worktree observation;
- fence compare-and-swap release before visible reservation removal;
- no compatibility alias, dual reader, dual writer, callback bag, runtime bag,
  or external admission dependency.

## Current execution owner

All current work is governed by the active OpenSpec Change
`native-lane-resolution-authority` and its design, tests, Claims, Chronicle, and
exact-HEAD proof. This archived plan must not be used to deploy software, invoke
an external command, construct a provider response, or authorize retirement.

## Closeout record

The historical plan is retained only to explain the rejected authority split and
the native invariants that replaced it. Its implementation steps are closed;
current lifecycle work proceeds exclusively through ETHOS
`status -> plan -> prove -> land -> publish` and native lane-resolution commands.
