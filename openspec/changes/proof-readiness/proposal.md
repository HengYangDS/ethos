# Proposal

## Why

A full proof already runs its readiness tier first: every gate that is not a test or package gate,
and does not depend on one. The tier is lint, hygiene, prose, schemas, projections, the audit and
the like. If any of them fails, the proof stops before host admission. An operator still has no way
to run that tier alone before launching a proof:

- `ethos prove --execute --gate <id>...` refuses with `quality_obligation_unproven:behavior` before
  running anything;
- the static checks run by hand are a hand-kept list of Nox sessions, which missed
  `repository-hygiene` on 2026-11-06 and cost proof `b2p1`.

Register row 19 records this.

## What Changes

- `ethos prove --readiness --execute` runs exactly the readiness tier of the full plan, with the
  same gate runner, and never waits for the proof slot or host load. It reports every test and
  package gate as `not_run`, never as passing.
- It writes no proof attestation, and its result can never satisfy landing. Its verdict passes only
  when every readiness gate passes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: an operator can run the readiness tier alone before a full proof.

## Impact

- `src/ethos/surface/cli/root/proof.py` and its tests.
- Out of scope: changing which gates belong to the readiness tier.
