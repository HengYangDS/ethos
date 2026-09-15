## Why

The OpenSpec report adapter can erase a failed native validation when its result
contains no invalid item, and ignores invalid items when the process exits zero.
Adopter feedback also requires INFO findings to remain informational rather than
becoming invented errors. A later publication observation can also erase known
peer progress in the result state. Preserve each result boundary at its owner.

## What Changes

- Reject unsuccessful validation independently of item diagnostics.
- Validate the consumed full-report structure and retain invalid-item failures
  regardless of process exit status.
- Preserve successful empty and INFO-bearing official reports without parsing
  Markdown or creating a second OpenSpec interpretation.
- Replay distinguishing cases through the public governance consumer and keep
  official early-sync and archive semantics unchanged.
- Preserve observed peer progress when later publication evidence is unknown;
  keep CLI and Attestation projections consistent without replaying applied peers.
- Validate the immutable hook runtime once at prepared branch admission, not
  again for result notifications or transactions with no governed update.
- Update the existing terminal plan and quality execution guidance from actual
  delivery, scope and dependency-expansion observations.
- Record bounded local cleanup and rule-consumer comparison evidence in existing
  research/plan owners; remove an unsupported adapter-availability claim without
  introducing CUE or a structural rewrite into this implementation batch.

## Capabilities

### Modified Capabilities

- `quality`: subject=validation-results; reuse=extend; change=modify

## Impact

The existing OpenSpec lifecycle report and publication result owners, their
direct tests and public consumers change. No dependency, persistent result store, adopter parser,
workflow graph or alternate intent carrier is added.

## Out Of Scope

- Reimplementing OpenSpec synchronization or Markdown validation.
- Changing history, signer trust, account associations or adopter repositories.
- Changing test budgets or parallelism to conceal validation cost.
