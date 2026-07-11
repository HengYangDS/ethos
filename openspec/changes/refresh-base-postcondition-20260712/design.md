## Context

`refresh_work_lane_base` captures the candidate head, invokes `git rebase`, and
then reports success from the subprocess result. The command's real semantic
effect is stronger: the Work Lane must now contain the captured candidate head.
An exit code only describes the child process; it does not establish that Git
references changed as required.

## Goals / Non-Goals

**Goals:**

- Bind a successful refresh report to the Git ancestry fact it claims.
- Keep ordinary semantic conflicts blocked and parity-projection recovery
  available.
- Exercise the exact false-success shape without relying on host signing or
  hook behavior.

**Non-Goals:**

- Introduce another workflow engine, ref protocol, or success state.
- Mask an unavailable signing identity or rewrite commits unsigned.
- Advance candidate or accepted branches as part of refresh.

## Decision

After all successful replay paths obtain the refreshed HEAD, ETHOS will verify
that the candidate HEAD captured before replay is its ancestor. If that fact is
absent, it returns a blocked result with
`refresh_base_postcondition_failed`; it does not advertise landing as a next
step. The check is placed after projection recovery as well, so recovery cannot
weaken the same invariant.

The candidate head remains the captured value, rather than a newly read ref:
the command proves the transition it actually attempted. A subsequent candidate
advance remains a separate freshness condition for landing.

## Risks / Trade-offs

- **A host returns success without changing refs** -> the new postcondition
  blocks rather than allowing a false lifecycle transition.
- **Candidate advances concurrently** -> the command truthfully establishes its
  captured base; normal land freshness checks still reject a stale lane.
- **Projection recovery changes control flow** -> one shared postcondition keeps
  the recovery path from becoming an exemption.

## Migration Plan

1. Add the OpenSpec delta and a red regression for zero-code no-op rebase.
1. Add the ancestry postcondition after both replay-success paths.
1. Run focused tests, formatting, lint, strict OpenSpec validation, and
   changed-scope proof on a stable owned lane.
1. Bind claim evidence, land through candidate, close out the accepted root,
   archive the carrier, and retire only the owned lane.

Rollback is a normal revert; no persisted state or data migration exists.
