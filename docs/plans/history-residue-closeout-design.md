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

## Expired Debt Carrier Attribution

The following deletion-time attribution preserves the ten records that expired
on July 18, 2026 after their live allowances are removed from the active rules
ledger. Category values are the measured carrier allowances recorded before
deletion; replacement text identifies the semantic owner that absorbed each
temporary carrier.

| Debt record | Owner | Replacement | Measured categories | Allowance | Wave |
| --- | --- | --- | --- | ---: | --- |
| `program-foundation` | `global-declarative-compression-program-20260711` | source budget, carrier admission, and declaration compiler foundation | `python_product`=352, `python_tests`=400, `python_tools`=250, `toml`=714, `json`=16 | 1,428 | `T5` |
| `candidate-train-reconciliation` | `global-declarative-compression-program-20260711` | candidate-train semantic integrations pending T8 scenario, runner, template, and provider-copy consolidation | `python_product`=1096, `python_tests`=2057, `python_other`=508, `shell`=368, `yaml`=4, `json`=102, `jinja`=15 | 3,237 | `T8` |
| `openspec-archive-preflight-20260712` | `openspec-archive-preflight-20260712` | collapse isolated archive preflight after the official lifecycle API exposes a source-safe dry-run receipt | `python_product`=253, `python_tests`=267, `yaml`=2, `toml`=80 | 602 | `archive-closeout` |
| `semantic-attestation-receipts-20260714` | `semantic-attestation-receipts-20260714` | compress the external semantic receipt verifier after receipt validation is shared with the evidence contract | `python_product`=84 | 84 | `semantic-attestation-compression` |
| `adopter-material-scope-binding-completion-20260714` | `adopter-material-scope-binding-completion-20260714` | compress scope-binding fixtures and duplicate lifecycle wiring after the shared companion read model is consolidated | `python_product`=428, `python_tests`=824, `jinja`=7 | 1,118 | `adopter-material-scope-compression` |
| `repository-text-layout-completion-20260715` | `repository-text-layout-completion-20260715` | consolidate shared text-layout diagnostics into native owner integrations after the active-carrier boundary is proven | `python_tools`=66, `python_tests`=113, `shell`=11 | 190 | `repository-text-layout-compression` |
| `adopter-lifecycle-claim-freshness-20260718` | `adopter-lifecycle-claim-freshness-20260718` | fold behavioral semantic-scope regressions into the existing lifecycle claim suite and remove the temporary claim-scope carrier after durable lifecycle evidence is refreshed | `python_tests`=89, `toml`=24 | 125 | `adopter-lifecycle-claim-freshness-compression` |
| `hosted-ci-remediation-20260717` | `hosted-ci-remediation-20260717` | archive the active carrier; retain only the existing owner script and focused regressions | `python_tests`=40, `shell`=12, `toml`=46, `yaml`=4 | 102 | `hosted-ci-remediation-closeout` |
| `bounded-status-read-model-20260718` | `refresh-base-ledger-merge-20260717` | consolidate bounded foreign-lane status fixtures and semantic rebase-recovery harnesses after coordination readers and ledger fixtures share one contract carrier | `python_product`=180, `python_tests`=528, `toml`=10, `json`=20 | 776 | `bounded-status-compression` |
| `dual-remote-reconciliation-admission-20260718` | `remote-reconciliation-admission-20260718` | fold dual-remote reconciliation receipt validation into the shared external-evidence contract after provider-neutral receipt verification is available | `python_product`=170, `python_tests`=157, `toml`=9 | 336 | `dual-remote-reconciliation-compression` |

The deleted records declared 7,998 eLOC in total. The unexpired
`node-runtime-compatibility-20260716` and
`repo-first-worktree-governance-bootstrap-20260718` records and their waves are
retained byte-for-byte.

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
