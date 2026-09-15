## Why

The OpenSpec report adapter can erase a failed native validation when its result
contains no invalid item, and ignores invalid items when the process exits zero.
Adopter feedback also requires INFO findings to remain informational rather than
becoming invented errors. Preserve the complete result boundary at one owner.

## What Changes

- Reject unsuccessful validation independently of item diagnostics.
- Validate the consumed full-report structure and retain invalid-item failures
  regardless of process exit status.
- Preserve successful empty and INFO-bearing official reports without parsing
  Markdown or creating a second OpenSpec interpretation.
- Replay distinguishing cases through the public governance consumer and keep
  official early-sync and archive semantics unchanged.
- Update the existing terminal plan and quality execution guidance from actual
  delivery, scope and dependency-expansion observations.
- Record bounded local cleanup and rule-consumer comparison evidence in existing
  research/plan owners; remove an unsupported adapter-availability claim without
  introducing CUE or a structural rewrite into this implementation batch.

## Capabilities

### Modified Capabilities

- `quality`: subject=validation-results; reuse=extend; change=modify

## Impact

The existing OpenSpec lifecycle report owner, its direct tests and public
consumer tests change. No dependency, persistent result store, adopter parser,
workflow graph or alternate intent carrier is added.

## Out Of Scope

- Reimplementing OpenSpec synchronization or Markdown validation.
- Changing history, signer trust, account associations or adopter repositories.
- Changing test budgets or parallelism to conceal validation cost.
