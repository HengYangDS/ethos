# Proposal

## Why

A placement that the artifact topology denies could not be emptied. On 2026-11-15 a governed
repository that migrates its hand-written pipeline to the generated one asked to delete ten shell
scripts under `.config/ci/scripts`, the directory the topology declares retired.
`ethos lane prewrite` refused each path with `retired_config_script_home`, with a worktree target
and with an index patch whose only effect is the deletion. The pre-commit hook runs the same
guard on staged deletions. The repository can neither edit the files nor take them away, so the
audit keeps reporting them and its migration cannot finish.

The cause is the order of two questions in the write guard. It turns a denied placement into a
refusal before it reads the effect, and it has the effect in hand: a tracked path that is absent
from the worktree, or the `delete` effect of a staged path. The rule holds for every denied
placement, not for this prefix alone.

The owner's rule of 2026-11-14 admits it to this batch: a defect that blocks a governed repository
does not count against the one off-gate row of a weekly batch. The fix narrows a refusal and adds
none, so the law freeze admits it too.

## What Changes

- The write guard admits the removal of a tracked path whose placement is denied. A creation or
  an edit there stays refused with the placement's gap.
- A test asks the guard for an edit, a worktree removal, a staged deletion and a staged creation
  of one path under a denied prefix.
- The Unreleased section of `CHANGELOG.md` gains a Fixed line.

Not breaking: no request that passed is refused, and a removal that was refused now passes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: ADDED requirement `A denied placement admits its own removal`.

## Impact

`src/ethos/adapters/admission/paths.py`, `tests/unit/lanes/hook/test_path_admission.py`,
`CHANGELOG.md` and `openspec/specs/repository-governance/spec.md` through this Change's delta.
