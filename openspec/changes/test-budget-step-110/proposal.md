# Proposal

## Why

The test ceiling is 105,000 line-equivalents, and `dev` at `d98081605` reads 104,753: 247 are
free. The rows of 0.2.0-beta.12 do not fit. The committee's resolution of 2026-11-14 numbers the
step as DR-0028 and lands it alone, first in that batch, with a measured removal.

The policy at a hard ceiling is to remove accidental complexity first and then to take one step
of 5,000. The removals were prepared on 2026-11-14 against a stack that held an unlanded row, and
were measured again on `dev` on 2026-11-15:

- Of the prepared removals worth 84.3 line-equivalents, about 52.5 apply to `dev` in four files.
  With them the tests read 104,701, and 299 are free.
- 7.0 conflict with three commits that landed since and need rework.
- 24.8 remove a test that only the adopter bump adds; they belong to that row.
- With the step, 5,299 are free of 110,000.

## What Changes

- DR-0028 records the necessity review: the removal measured on the landed tree, what remains
  and why one step follows.
- The test ceiling moves to 110,000.
- The four-file removal lands with it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The source budget policy, four test files, one decision record and its index entry. The
`rc-gate-successor` Change holds this number for the record.

Owner: the release lead. Next action: redo the removals on `dev` and write the record with those
figures. Read again: at the cut of 2026-11-19; it lands alone on 2026-11-23.
