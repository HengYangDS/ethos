## Why

The verification cycle spends time waiting for unrelated gates and discovers
cheap source failures after costly tests have already started. The existing
runner correctly blocks failed dependencies, but unit testing declares none of
its inexpensive source-readiness requirements. Barrier-separated waves also
hold a newly ready gate behind an unrelated slow peer.

## What Changes

- Execute the admitted dependency graph with one bounded ready-node scheduler,
  retaining exclusive writers, failed-dependency blocking and stable results.
- Declare inexpensive source-readiness prerequisites for the heavy test gate in
  the existing gate registry; retain independent diagnostics after failure.
- Exercise concurrency, failure propagation, writer isolation and public proof
  transport without constructing a full lifecycle fixture for scheduler tests.
- Record full-cycle acceleration priorities in the existing terminal plan and
  use the authorized independent 45000 ELOC ceilings instead of line trimming.

- Resolve all 25 native specification length issues by preserving obligations
  and scenarios, separating genuinely independent semantic contracts. This scope
  was explicitly requested after official validation exposed the issues.

## Capabilities

### Modified Capabilities

- `quality`: dependency-driven fail-left execution without wave barriers.

Other affected specifications receive editorial clarification and semantic
regrouping only; their obligations remain unchanged, not new capabilities.

## Impact

The shared gate runner, its proof/local-CI consumers, gate declarations, focused
regressions, native budget policy and existing terminal plan. No new service,
persistent scheduler state, lane, dependency or parallel roadmap.

## Out of Scope

Cross-HEAD evidence reuse, fixture supply redesign and publication diagnostics
remain separate bounded work in the terminal plan. This Change neither claims
to finish them nor weakens coverage, proof identity or effect-time authority.
