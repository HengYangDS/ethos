# Proposal

## Why

The archived `rc-plan` design gives a workstation a fast tier: what the full proof and the forges
would say, learned in minutes. Its Family 4
(`openspec/changes/archive/2026-11-07-rc-plan/design.md`, lines 104-109) says that "`fast-tier`
adds architecture and import-selected tests to readiness", and its decision 4 (line 182) gives the
row "selection from recorded facts". The committee's resolution of 2026-11-14 places the row in
0.2.0-beta.13, and DR-0029 (`docs/decisions/dr-0029-release-candidate-gate-successor.md`, line 85)
names the fast tier among the rows that a later cut may not drop.

Three facts of 2026-11-15 belong to its acceptance:

- A change to a document selected no test, because selection followed imported modules. A link
  added to a page that an installation carries failed a test on the forge first. The release
  lane's own tool, outside the product, now selects the tests that name a changed path or stage
  the package.
- Five sessions ran only on the forges, and nothing listed them for a workstation. The batch of
  0.2.0-beta.12 added a sixth, the suite leg, so a list kept by hand was stale within two days.
- One governed product's session met 16 problems in eight hours. Twelve were found late, and each
  of the twelve had a check of less than two minutes.

A fourth fact needs no work. On 2026-11-15 a cache directory that Git ignores failed readiness 80
minutes after the command that made it, while the tree read as clean. The readiness gate
`repository-audit` already reports such a directory as `generated_artifact_root_cache_drift`, so
the readiness run finds it as soon as it is run.

At the base the product selects no test. `ethos prove --readiness --execute` runs the readiness
gates and names the other gates as not run; it says nothing about the tests that a change reads,
or about what only the forges run.

## What Changes

- The result of `ethos prove --readiness --execute` gains `data.unexamined`. It names what the run
  did not examine, refuses nothing and changes no verdict.
- On a Work Lane, a path committed since the candidate branch selects its readers among the Python
  tests, each with one reason: the test itself changed; a changed `conftest.py` is above it; it
  imports the changed file, or a file that imports it; its text names the changed path; or the
  package carries the path and the test's text names the wheel's carried-file table, so it stages
  the package. ETHOS runs none of them: the caller runs them with the native runner.
- A changed path that no test reads is listed, so that an empty selection is not read as "nothing
  to run".
- The result lists each task-runner session that a step of the pipeline files asks for and that no
  planned gate's command asks for, with the jobs that ask. It reads the pipeline files that the
  pipeline model generates, and no second list.
- A part that cannot be read, such as a candidate branch that does not resolve, is named as
  unavailable. The gates alone decide the verdict.
- The command reference states the field, and that a passing readiness run is neither the full
  proof's pass nor the forges' pass.

Out of scope, each with its reader: running the selected tests under a host ticket (read again at
the cut of 0.2.0-beta.14, with `gate-reuse`); selection from recorded facts and whole-repository
tests (with `test-tiers`); the late gates that a changed path reads (with `gate-reuse`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a readiness run names what it did not examine, and a change selects the tests that
  read it.

## Impact

- `src/ethos/application/proof/`, `src/ethos/repository/policy/quality/selection.py`,
  `src/ethos/repository/paradigm/orchestration.py` and their tests.
- One result gains one field. No command, operation, flag, gap code or refusal is added, and no
  existing invocation changes its verdict.
- The 900-second requirement is untouched: a full proof does not call the report.

Owner: the release lead. Next action: land the patch with the batch of 0.2.0-beta.13. Read again:
at the cut of 0.2.0-beta.14, for the remainder above.
