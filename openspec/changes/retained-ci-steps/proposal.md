# Proposal

## Why

The repository paradigm requires every CI step to invoke one native command or toolchain-owner
task. At ETHOS `c4e5a351f` it reports 57 inline shell steps in aigw-cli and 37 in
openai-responses-proxy.

- **Orchestration.** Some of these steps can be replaced by a product command or by native Forge
  configuration.
- **Operating-system glue.** Others are glue that a fresh runner needs before any toolchain exists.

The user's native-execution rule lets such glue stay when its owner, necessity, exact scope and
target-platform evidence are recorded. The paradigm has nowhere to record them, so it is stricter
than that rule and leaves necessary glue with no conforming home. On 2026-10-19 the user decided to
refine the paradigm before adopters convert their pipelines.

## What Changes

- A CI step that holds a shell program conforms when the repository's retention record,
  `.config/ci/retained-steps.toml`, describes it fully:
  - it names the step by Forge file, job and the SHA-256 of its exact step text;
  - it gives the class, either `official-installer` or `operating-system-glue`;
  - it gives the owner, reason, platforms and target-platform evidence.
- Each job that a record lists must still carry a step with that digest. A `retained-step` gap is
  reported in four cases:
  - the record is incomplete;
  - its class or platform is uncatalogued;
  - its digest is malformed;
  - a listed job no longer carries the step.

  An edited step therefore reports inline shell again, and its record reports as stale.

- The record admits only inline shell in CI steps. Gates, and steps that run tracked scripts, stay
  as strict as before.
- The paradigm checks only that a record is complete and current. Whether the evidence shows
  target-platform necessity is judged in the review of the adopting repository's Change.

Out of scope:

- Converting adopter pipelines. Each adopter does this in its own Change.
- Admitting executor-generated scripts. The tracked-script generator records already cover them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: native repository orchestration admits recorded official installers and
  operating-system glue in CI steps.

## Impact

This Change touches:

- the paradigm catalog (`src/ethos/contracts/paradigm/paradigm.toml`) and its declaration model;
- the orchestration obligation (`src/ethos/repository/paradigm/orchestration.py`) and its
  regressions;
- DR-0012's consequence for scripts;
- the changelog.

Adopters gain one optional carrier in the `ci` configuration plane. A repository without retained
glue keeps none.
