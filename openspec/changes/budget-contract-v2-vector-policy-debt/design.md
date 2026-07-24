## Context

Task 4 is archived and landed. Historical v1 replay is complete, but its v2
observation is intentionally null. The selected C1 v2 replay is blocked by
`source_budget_native_parse_failed:yaml:.config/ci/templates/hosted/gitlab-ci.yml`.
Task 5 must therefore separate reusable strict contracts from repository
activation: synthetic complete observations exercise the reducer, while the
tracked repository declaration stays inactive and the sole debt successor stays
unmapped.

## Decisions

1. **No compensation across coordinates.** The semantic key is
   `(scope_id, metric_id)` and `unit` is a bound invariant. Every coordinate is
   evaluated independently and the overall verdict is logical AND.

2. **Vectors are canonical typed tuples.** Directly parsed vectors must be
   unique and sorted. Canonical constructors sort before hashing. Dictionaries
   are not used because they hide duplicate keys and cross-unit forgeries.

3. **Policy state is a discriminated union.** `inactive` carries campaign and
   lifecycle identity but no baseline or terminal vectors. `shadow` carries a
   complete immutable baseline binding, terminal vector, permanent allocations,
   settled reductions, and Debt v2. Task 5 adds no authoritative cutover state.

4. **Debt mapping is a discriminated union.** `mapped` records bind origin,
   admitted HEAD, canonical scope, inventory/contract identity, allowance and
   expected-deletion vectors. `unmapped` records carry no enforceable allowance
   and list exact missing bindings.

5. **Task 4 remains the observation owner.** Its existing shadow observation is
   promoted to a public type rather than duplicated. The verdict input wraps
   baseline/current observations and mapped-debt replay bindings only.

6. **The reducer is pure.** It receives typed observations, policy, and `date`.
   It performs no filesystem, Git, environment, config, or clock reads.

7. **Trust failures precede arithmetic.** Missing/incomplete observations,
   baseline identity mismatch, coordinate-set/unit mismatch, unmapped debt, and
   invalid/expired/stale debt block and contribute zero allowance.

8. **Date boundaries are inclusive.** A record or wave due on a given date is
   active on that date and becomes expired/overdue the next day.

9. **Repository activation is explicitly deferred.** The tracked v2 policy is
   `inactive`, preserves baseline HEAD
   `2dab77f169eceb2d45f917358c2a7487e7ac8db6`, binds campaign
   `global-declarative-compression-program`, and records
   `node-runtime-compatibility-20260716` as unmapped.

10. **Schema versions coexist.** The published source-budget schema is a
    composition of the unchanged v1 policy union and the v2 policy union; the v1
    loader and v1 table remain behaviorally unchanged.

## Failure Semantics

The reducer accumulates stable required gaps but emits no coordinate arithmetic
when policy or observation trust is incomplete. Invalid, expired, overdue,
stale, or unmapped debt never contributes allowance. Campaign-terminal growth
and valid active debt are advisories only when no required gap exists.
Transition breaches and terminal breaches are blocking. Terminal mode also
blocks while any debt remains active.

## Rollback

Remove the v2 policy module, verdict module, sibling loader/table, composed
schema branch, and focused tests together. Keep the accepted Task 4 envelope and
all v1 contracts/config/reducer behavior unchanged.

## Acceptance

- The repository v2 declaration loads as typed `inactive` and the v1 declaration
  remains byte-for-byte unchanged.
- Duplicate, unordered, forged, cross-unit, cross-scope, underflowing, or
  incomplete vectors are rejected.
- Unmapped debt carries no allowance and always blocks evaluation.
- Complete synthetic replay inputs demonstrate deterministic logical-AND
  verdicts, inclusive lifecycle boundaries, and zero allowance from invalid
  debt.
- The node-runtime successor remains unmapped; no admitted SHA is inferred.
- Focused tests, owner quality gates, lifecycle, Claims, parity, and exact-HEAD
  proof pass before archive and closeout.
