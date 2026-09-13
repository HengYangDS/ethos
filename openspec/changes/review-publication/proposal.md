## Why

Proposal publication currently requires candidate integration and a completed
Change proof. A developer therefore cannot submit an unfinished review snapshot
without prematurely archiving its intent. Detached CI also cannot evaluate the
same target-role/OpenSpec boundary without reconstructing host lane state.

## What Changes

- **BREAKING** Admit review-object publication independently of accepted-product
  proof; keep exact object trust, introduced commit policy and peer-local CAS.
- Resolve target-role and active-intent obligations from explicit Git coordinates
  through one read-only owner shared by publication, pre-push and detached CI.
- Preserve repository proof and closeout requirements for accepted/release
  targets, including a request mixing review and accepted targets.
- Revalidate actual target obligations when applying a persisted request; a
  carried proof-selection string cannot weaken the current admission boundary.
- Remove candidate-checkout-only review admission and its superseded tests and
  documentation. Keep proposal refs non-authoring and work/candidate refs local.

## Capabilities

### Modified Capabilities

- `repository-governance`: exact review projection and role-bound publication.
- `command-plane`: public detached-CI observation of explicit ref updates.

## Impact

Existing publication policy, Git admission, publication planning/execution,
OpenSpec tree observations, hook CLI, related tests and current documentation.
No new dependency, persistent lifecycle, adopter carrier or forge-specific
parser. The terminal contract and source graph bindings follow the same meaning.

## Non-Goals

No candidate synthesis, forge merge automation, proposal deletion API, runtime
retention redesign or architecture rendering. Review admission is not completed
product acceptance, mutation authority, or proof of user benefit. AIGW and Proxy
remain untouched.
