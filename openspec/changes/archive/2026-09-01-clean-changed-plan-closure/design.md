## Context

See `proposal.md`. The current resolver always asks OpenSpec for a current or
archived Commitment before the planning command can interpret the fresh changed
set. That ordering lets historical intent manufacture work for an empty current
observation.

## Goals / Non-Goals

**Goals:**

- Make fresh Git changed paths the entry condition for changed-scope planning.
- Return one deterministic successful no-op result for an empty set.
- Keep archive authorization strict for every non-empty changed set.

**Non-Goals:**

- Change proof or archive admission for real changes.
- Add a new persisted carrier, registry, fallback, or compatibility path.
- Refactor the wider result algebra or lifecycle UX in this atom.

## Decisions

The `plan` command terminates before current intent resolution when `--changed`
is requested and fresh status reports no changed paths. This is preferable to
weakening `archive_scope_gaps`: the latter protects real archive transitions,
whereas an empty changed set has no effect to authorize at all.

The no-op result uses the existing `EthosResult` algebra and contains no
Commitment or TransitionPlan payload. Historical Attestations remain durable
evidence, but are not selected as current intent without a current changed
subject.

## Risks / Trade-offs

- A caller may previously have used `plan --changed` on a clean checkout as an
  indirect way to inspect the last archive. That behavior is rejected because
  it conflates historical evidence with current work; Attestation queries own
  historical inspection.
- The early return must occur only for explicit `--changed`; ordinary planning
  and explicit `--change` retain their existing semantics.

## Migration Plan

Add a command-level RED that reproduces the clean accepted repository failure,
implement the early no-op boundary, retain the existing kernel tests that prove
non-empty stale archive scope is rejected, and validate the exact public JSON.
