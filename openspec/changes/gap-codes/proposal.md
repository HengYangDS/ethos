# Proposal

## Why

The release gate's R1 requires registered gap and exit codes, help text for every parameter and
JSON usage errors, and only the third exists. Row A13 of the release-candidate plan is the place
this Change fills: Decision 2 puts gap and exit vocabularies in Family 2, and Appendix A.2, A.3 and
A.11 item 13 name the registry, the exit table and the static test. The gap census of 2026-11-14
finds 1,552 distinct codes at 2,228 sites in 274 product files and none registered; ten exit sites
agree by convention, not by a table, and only prose states why each number means what it does. The
owner approved the RC scope on 2026-11-14, and this is the beta.11 slice, tagged 2026-11-21.

## What Changes

- A gap registry as packaged data, one row per code: its owner package, and where true its
  meaning, detail and fixed repair. Composed names register by their code with a `detail`, and
  the prefixes of names assembled from parts register as `[family]` prefixes.
- A standard-library loader that reads a gap's code, whether a code is registered, and a row's
  repair; it reports an unregistered code instead of swallowing it.
- A two-way static test: every code a refusal or raise site carries is registered or a family
  member, and every registered code occurs in the sources or is declared reserved. The 615 codes
  that only flow through data have no bounded syntactic rule and are left to a runner guard, as
  the plan recommends, rather than to an approximate match.
- The shared CLI test runner refuses a result whose gap code is unregistered, naming the code.
- One exit table in the kernel: `pass` 0, `blocked` 1, `usage` 2, `undelivered` 3, `process` the
  child's status and `refused` 125 reserved. The CLI exits by kind, and `ethos --help --json`
  prints the table. No exit number changes in this Change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kernel`: ADDED requirement `Gap codes are a registered vocabulary`.
- `command-plane`: ADDED requirement `Process exits follow one declared table`.

## Impact

`src/ethos/contracts/codes/` (new package and its table),
`src/ethos/contracts/operations/declaration.py`, `src/ethos/surface/cli/output.py`,
`src/ethos/surface/cli/catalog.py`,
`tests/support/ethos_cli_runner.py`, two new test modules, `CHANGELOG.md` and a
`docs/reference/command-plane.md` line. This Change lands last in its beta.11 batch: every Change
that adds, renames or moves a code adds its row or the static test fails.
