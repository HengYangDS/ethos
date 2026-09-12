## Why

A current `ethos prove --full` run can reattach archive authority from a
historical Change when the current Git changed scope is empty. The resulting
archive-scope check compares historical paths with an empty current scope and
blocks an otherwise no-op proof with `proof_archive_scope_stale`.

## What Changes

- Make full proof treat an empty current changed scope as no current archive
  authorization subject, rather than reusing historical archive authority.
- Preserve strict archive-scope validation whenever the current changed scope is
  non-empty and archive authority is applicable.
- Add regression coverage for both the empty-scope no-op and the non-empty
  fail-closed boundary.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Full proof planning must distinguish an empty current
  changed scope from a non-empty scope that requires historical archive-path
  validation.

## Impact

`src/ethos/adapters/mutation/proof.py` will select archive authority only for a
non-empty current scope. `tests/unit/kernel/test_proof_plan_binding.py` will
cover the boundary. No historical OpenSpec artifact, Attestation, archive effect,
or public command is removed; the change only prevents historical authority from
being applied to an empty current fact set.
