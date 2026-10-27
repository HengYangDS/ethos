# Proposal

## Why

`knowledge-currency` corrected the repository-governance requirements that describe removed runtime, status, publication, documentation and supply behavior. The repository paradigm caps every Markdown file at 512 nonblank lines, and a Change carries one delta file per capability, so the 11 Work Lane coordination findings of its audit follow here.

The audit of 2026-10-27, verified again against the code before this Change, found that these requirements describe mechanisms the code no longer has:

- Chronicle as the record of a handoff or a policy binding;
- parity projection and its recovery during a base refresh;
- preservation and recovery packages before retirement, where retirement now hashes reviewed content into one exact receipt and removes it;
- lane-resolution Decisions, Receipts and the `preserve-retire` decision;
- episode claims and Claim binding on a Lease;
- the subject-keyed lease schema;
- per-ref push dry-runs, where publication now persists one dry-run plan and applies one atomic exact-lease push;
- detail-state fields that the status readers no longer report.

## What Changes

- **Modified, titles kept (5).** Cohort-bound convergence, final declared-peer proposal absorption, local-state schema evolution, coordination detail state and Lease generation identity restate their full text with the current mechanism.
- **Replaced under new names (6).** Context-bound mutation admission, Work Lane lifecycle resolution, refresh success, resolution Decisions, authorized cohort closeout and the preservation of dirty and unbound content each carry a title or scenario that names a removed mechanism. OpenSpec matches scenarios by name, so each is removed and added under a name that states the current obligation.
- **CHANGELOG.** One line under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: the Work Lane coordination requirements match the current Lease, handoff, refresh, retirement and status behavior.

## Impact

- Accepted spec text only; no code changes.
- Completes the repository-governance corrections that `knowledge-currency` began.
