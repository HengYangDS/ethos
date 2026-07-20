## Context

`.config/checks/ruff/ruff.toml` is the Python policy owner, and
`tools/ci/scripts/run-python-lint.sh` is its executable owner. `ARG002` is
suppressed twice even though its only finding is the execution root declared by
`DryRunRunner.run`.

## Design

Dry-run planning resolves the supplied root and still returns a planned action;
it never executes the action. With the only diagnostic removed, `ARG002` leaves
both exception carriers and is evaluated by the existing canonical Ruff owner.
No alternate command, policy, or compatibility path is added.

## Alternatives

1. Keep a zero ratchet baseline: rejected; this still suppresses direct rule
enforcement.
2. Rename the argument with a leading underscore: rejected; this hides rather
than fulfills the execution-root contract.
3. Resolve the root during dry-run planning: selected; it preserves contract
semantics without action execution.

## Proof Strategy

Prove focused contracts, the tracked-corpus `ARG002` probe, the canonical lint
owner, strict OpenSpec validation, and a current-HEAD proof before integration.
Candidate, accepted closeout, publication, and lane retirement remain distinct.
