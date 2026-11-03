# Proposal

## Why

Git's reference-transaction hook input reports a deletion whose caller gave no old value, as
`git branch -D` and `git update-ref -d` do, with zero old and new values. Git 2.56.0 also runs the
hook again for every deletion of a ref that `packed-refs` holds, for the packed backend's own
transaction, with the same zero-to-zero line and before the line that carries the old value.
ETHOS's hook protocol governs zero-to-zero lines, since they can delete a protected branch, but
`resolve_ref_move_policy` finds no policy for zero values, so every such line is refused with
`ref_move_policy_unavailable`.

- On 11-03 `ethos lane retire absorbed-ref --apply` failed with `git_effect_cas_rejected` for
  di-effect's `integration/dev`, which is loose and still in `packed-refs`, and for Alphasim's
  `work/ci-local-orphaned-board-test-20260714`, which is only packed, after previews that passed.
  With the alpha.28 runtime, the line that carries the old value resolves a policy for
  `integration/dev`.
- Reproduced with Git 2.56.0: deleting a loose ref with its old value reports one line, `old 0`;
  a packed, or packed and loose, ref reports `0 0` and then `old 0`; `git branch -D` and
  `git update-ref -d` report only `0 0`.

## What Changes

- The hook protocol governs a prepared zero-to-zero line for an existing ref as the deletion of
  that ref's current value. Every existing policy, the protected-branch rules and prepared
  retirement intents then apply as they do to a deletion that names its old value.
- A zero-to-zero line for a ref that does not exist keeps its zero values and stays refused.
- A deletion without an old value is now judged by what it deletes instead of being refused for a
  missing policy, as the same deletion with its old value already is.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the hook protocol governs a deletion without an old value by the ref's current value.

## Impact

`_reference_transaction` in `src/ethos/adapters/repo/hook/protocol.py`, the hook protocol and
absorbed-ref retirement tests, and the changelog.
