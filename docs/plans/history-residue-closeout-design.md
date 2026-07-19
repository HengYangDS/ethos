---
subject: ethos:history-residue-closeout-design-20260719
role: plan
state: active
relations:
  implements: history-residue-closeout-20260719
  canonical_for: history residue closeout topology and deletion budgets
---

# History Residue Closeout Design

Status: active.

Purpose: define the implementation topology, safety boundaries, and measured
deletion limits for the July 19, 2026 history-residue closeout.

See also: [OpenSpec change](../../openspec/changes/history-residue-closeout-20260719/)
and the [implementation plan](history-residue-closeout-implementation.md).

Date: 2026-07-19

## Decision

Close the product checkout's tracked and ignored historical residue in one owned
Work Lane, but keep four evidence classes distinct:

1. tracked configuration/scaffold truth changes;
2. ignored local-state maintenance effects;
3. operator-owned recovery archive material;
4. measured source-budget deletion and its tracked debt ledger.

The normative requirements live in
`openspec/changes/history-residue-closeout-20260719/`. This document records the
implementation topology and deletion budgets used to execute them.

## Active Owners

| Concern | Owner |
| --- | --- |
| Rules normalization and migration | `ethos.repository.policy.rules` plus `ethos.surface.cli.rules` |
| Project/release/assistant scaffold parity | `ethos.repository.adoption.scaffold` |
| SQLite schema | `ethos.adapters.store.state.events` |
| Lease maintenance | `ethos.adapters.store.state.lease` |
| Proof retention | `ethos.adapters.mutation.proof` |
| Local-state operator entrypoint | existing `ethos doctor` inspection surface |
| External receipt semantics | `ethos.adapters.admission.evidence.external` |
| Recovery archive | operator archive plus tracked Chronicle digest receipt |
| Compression accounting | `ethos quality source-budget` and `.ethos/rules.toml` |

## Deletion Contract

After removing the ten records expired on July 18, 2026 and retaining only the
two unexpired allowances, live inventory must not exceed:

| Category | Limit | Required net deletion from entry state |
| --- | ---: | ---: |
| `python_product` | 35,675 | 2,887 |
| `python_tests` | 46,865 | 4,662 |
| `python_tools` | 1,038 | 270 |
| `python_other` | 446 | 502 |
| `shell` | 1,552 | 402 |
| `toml` | 11,846 | 1,263 |
| `jinja` | 671 | 35 |

The category total is 10,021 eLOC. Moving code between categories, resetting
the baseline, extending expiry, or issuing umbrella debt is not settlement.

## Local-State Safety

- SQLite v2 drops `cache_entries` only when it is empty; otherwise migration
  fails and leaves v1 recorded.
- Lease deletion binds exact ID, subject, expiry observation, absent ref,
  absent linked worktree, and absent recorded path.
- Proof deletion protects current HEAD, every ref-reachable commit, every
  worktree HEAD, and every live lease expected HEAD.
- Maintenance dry-run emits an inventory digest; apply recomputes it and rejects
  any state drift.
- Recovery snapshots are copied completely. The source directory is deleted
  only after entry digests, archive digest, extraction, and all bundle
  verifications pass.

## Rollback

Tracked changes roll back through Git. SQLite, proof, and snapshots are copied
to the operator archive before mutation. A failed local-state apply restores the
copy and does not reuse a stale inventory digest.
