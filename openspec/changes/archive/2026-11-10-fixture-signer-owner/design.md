# Design

## Context

See the [proposal](proposal.md) and the Phase T design draft 2 (scratch,
`build/runtime/work/catalog-root/phase-t/repository-spec-draft-2.md`, Step 1), reviewed in review 1
(Answer 2 row 1, advisory A1).

## Goals / Non-Goals

Goals: one signer owner; one build resolution per worker for fixture runtime installs.

Non-Goals: the `RepositorySpec` seed (Step 2) and any template cache.

## Decisions

1. The owner returns the anchor, so the 14 test lines that read or replace the own signer's
   `trust/allowed-signers` and `signer.pub` keep their layout under `own=<dir>`.
2. The build memo is process-local and keyed by the source root of `ethos.__file__`. An `ethos`
   profile root keeps `expected_runtime_build`, which a self-hosted install needs.
3. Measured in a scratch clone at `5ab05f098`, with interleaved runs of 236 tests and 178 installs:
   - resolutions per install fell from 2.000 to 0.022 (one per worker);
   - on the same dirty tree, wall time fell from 175 and 188 s to 116 and 118 s;
   - CPU fell from 678 and 722 s to 426 and 441 s.

## Risks / Trade-offs

- Editing the ETHOS checkout during a test session makes every later fixture runtime in that worker
  stale, where before only tests that straddled the edit were affected. Proofs run on committed
  trees and are unaffected.
- The clean-tree timing after the change is unmeasured, since it needs a commit (estimate: about
  12 % wall time on the timing set).
