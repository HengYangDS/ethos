## Why

A real public proof on isolated current-source fixtures returns pass after a gate
changes tracked content without moving HEAD. Checks read a mutable checkout while
issuance validates only commit coordinates and Lease, so the exact-commit claim
can describe different inputs from those actually checked.

## What Changes

- **BREAKING**: exact-commit proof requires source and index correspondence before
  execution, after execution, and when issuing/selecting the new result.
- Bind the execution-source observation into existing transient Facts and the
  carried proof plan, not another authority store or workflow.
- Reject tracked, index, policy and non-ignored input drift. Preserve diagnostics,
  leave user changes untouched, and permit declared ignored output generation.
- Keep dirty exploratory checks available as non-authorizing host observations;
  their results cannot be promoted into exact-commit proof.
- Explicitly distinguish sampled source stability from hostile same-UID isolation.

## Capabilities

### Modified Capabilities

- `quality`: exact-commit execution evidence must describe the source actually
  checked, with currentness validated at its owning boundary.

## Impact

Existing proof compilation, execution, issuance/selection, native Git content
observation, focused public regression tests and the single terminal plan.
No adopter writes, history rewriting, new lane, new result database or language
migration. Archived dependency audit remains pending accepted closeout until this
proof-integrity repair can safely verify the combined exact candidate.
