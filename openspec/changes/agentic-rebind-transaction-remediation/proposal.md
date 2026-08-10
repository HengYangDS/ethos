# Agentic rebind transaction and remediation

## Why

ETHOS already enforces exact Lease and Git coordinates, but callers still have
to reconstruct those internal coordinates manually for Commitment evolution.
The first hook failure therefore does not reliably lead a new agent to the one
safe public recovery operation. Separately, an authenticated archive effect can
be accepted by plan, prove, and land while status re-evaluates the archived
paths against the former active carrier glob and reports a contradictory scope
gap.

## What changes

- Make an authenticated archive effect the path authority for the exact archive
  transition across status, plan, prove, and land; missing or tampered effect
  evidence remains fail closed.
- Add a read-only Commitment rebind derivation that observes the current Lease,
  HEAD, index, overlay, and signed target commit and emits one immutable,
  digest-bound request receipt.
- Let rebind apply consume that receipt and revalidate every mutable coordinate
  rather than requiring callers to copy internal fields.
- Return a dedicated Commitment-rebind blocker, the discovered target commit,
  typed mismatches, partial effects, and one copy-safe remediation command.
- Distinguish a missing invocation actor from a genuinely different holder and
  keep valid-Lease editor-root remediation local to editor binding.

## Out of scope

- Weakening Lease, signature, hook, exact-CAS, or Commitment checks.
- Adding another state database or compatibility command plane.
- Implementing controller fencing, resumable long-running operations,
  transition-graph projection, traceability matrices, or proof caching in this
  atomic Change. Those require separate model changes after the shortest safe
  rebind path is closed.

## Affected capabilities

- `command-plane`: derive, receipt-bound apply, typed remediation, and bounded
  public diagnostics.
- `repository-governance`: current-generation attribution and exact Work Lane
  Commitment evolution.
