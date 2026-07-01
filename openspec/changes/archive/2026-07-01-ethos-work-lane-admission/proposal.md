# Proposal: Work Lane Admission

## Summary

Make ETHOS enforce Work Lane admission as product behavior instead of relying on
agent memory. The command plane must identify foreign `work/*` lanes, block
tracked writes from protected roots, require editor-root binding before writes,
and acquire ignored local leases when starting a new lane.

## Motivation

ETHOS already described Work Lane discipline, but the product repository lacked
the admission layer that prevents an agent from touching another active lane or
mutating an accepted root through raw git habits. The gap is systemic: a lease
table existed, yet status, mutation, and CLI flows did not consume it.

## Scope

- Add `ethos lane status`, `ethos lane prewrite`, and `ethos lane start`.
- Extend workspace status with linked worktree roles and foreign lane gaps.
- Gate `land --apply` and `publish --apply` on Work Lane role admission.
- Record lane leases in ignored SQLite local state.
- Update docs, claim evidence, and tests.

## Non-goals

- Do not read or dispose of foreign Work Lane content.
- Do not turn leases into repository truth.
- Do not push or mutate remote state.
