---
subject: ethos:history-residue-closeout-design-20260719
role: plan
state: active
relations:
  implements: history-residue-closeout-20260719
  canonical_for: bounded tracked history residue closeout
---

# History Residue Closeout Design

Status: active successor-v2 design.

Purpose: define the tracked cleanup, evidence, and safety boundaries for the
July 19, 2026 history-residue closeout.

See also: the normative
[OpenSpec change](../../openspec/changes/history-residue-closeout-20260719/)
and the [implementation plan](history-residue-closeout-implementation.md).

## Decision

Complete tracked cleanup in one owned Work Lane while keeping these evidence
classes separate:

1. tracked configuration, scaffolds, source, tests, docs, and claims;
2. ignored local-state capabilities exercised only in fixtures or copied state;
3. real operator maintenance effects, which are not authorized here;
4. campaign-terminal source-budget observation, which is not terminal settlement;
5. local proof, candidate/accepted closeout, remote publication, and hosted
   observation.

## Current Scope

- Lossless Rules V2 migration and guarded public apply.
- Product/scaffold parity for project, release, assistant, and rule surfaces.
- SQLite v2, conservative maintenance, archive verification, and proof-retention
  capabilities without real-state apply.
- Retirement of bundled verifier executables, non-authoritative performance
  evidence, and the structural blank-line gate.
- Restoration of unproven claim deletions and bounded disposition of the three
  provider-related claims.
- Exact closeout control and candidate-HEAD binding.

## Explicit Exclusions

- No real database, lease, proof, snapshot, ref, or worktree maintenance effect.
- No operator recovery archive or source deletion.
- No source-budget baseline, target, debt, expiry, or terminal-completion change.
- No compatibility alias, shim, forwarding module, or duplicate command plane.
- No hosted or remote claim derived from local evidence.

## Active Owners

| Concern | Owner |
| --- | --- |
| Rules normalization and migration | `ethos.repository.policy.rules` and `ethos.surface.cli.rules` |
| Project/release/assistant scaffold parity | `ethos.repository.adoption.scaffold` |
| SQLite schema and local-state capability | `ethos.adapters.store.state` |
| Proof retention | `ethos.adapters.mutation.proof` |
| External receipt semantics | `ethos.adapters.admission.evidence.external` |
| Closeout controls | `ethos.adapters.mutation.closeout` and admission owners |
| Compression observation | `ethos quality source-budget` and the global campaign |
| Claim integrity | `ethos.repository.evidence.claims` |

## Safety Contract

- Rules migration returns a structured gap and preserves source bytes whenever
  it cannot isolate or validate the target.
- SQLite v2 fails closed on unsafe state and is not applied to real state here.
- Lease and proof deletion require an explicit digest-bound apply and are not
  inferred from tests, archive, land, or closeout.
- Recovery deletion requires an independently verified operator archive and does
  not occur in this change.
- Historical claims remain unless a claim-specific transition records their
  current disposition.
- Source-budget campaign growth and terminal non-attainment remain visible as
  advisories; invalid, stale, expired, or over-cap debt retains canonical
  blocking semantics.

## Execution Order

1. Replay predecessor semantics onto the successor lane.
2. Repair semantic regressions and restore evidence carriers.
3. Reconcile OpenSpec, canonical plans, Chronicle, and claims.
4. Run focused and full verification.
5. Officially refresh from current candidate.
6. Regenerate parity and produce HEAD-bound proof.
7. Archive, inspect canonical fusion, land, and close out accepted root.
8. Keep remote publication and hosted observation as separate evidence.

## Rollback

Tracked changes roll back through Git. No real local-state effect is included in
this plan, so no state restoration is asserted.
