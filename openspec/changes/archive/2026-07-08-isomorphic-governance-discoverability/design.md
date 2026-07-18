## Context

The accepted repository-governance specification already says that every
governed repository emits `governance_context`, identifies the subject as a
repository, uses the same transition command semantics, and keeps profile or
adapter differences from creating a second product command plane.

The repo-local product boundary is reader discoverability: `README.md`, the
Product Design Contract, the glossary, and architecture tests. This lane does
not change runtime semantics; it makes the existing contract visible earlier and
harder to regress.

## Design

Keep one sentence of force and three boundaries visible:

1. ETHOS governs the ETHOS product repository and adopted repositories through
   the same kernel.
2. Differences belong to profiles and adapters: admission, checks, proof depth,
   provider surfaces, and domain shape.
3. This is not product cloning: ETHOS does not absorb another repository's
   domain model or create a second command plane.

The regression test normalizes whitespace before checking anchor phrases so the
docs can remain readable while preserving grep-friendly terminology.

## Alternatives

- Leave the idea only in JSON payloads and deep docs: rejected because first
  readers and agents need the contract before choosing a mutation path.
- Add a new command or profile object named after the concept: rejected as entity
  multiplication; the existing kernel, profile, and adapter model is sufficient.
- Reuse the archived `isomorphic-governance-kernel` change as an active carrier:
  rejected because archived changes are history, not reusable active work.

## Proof Strategy

- Focused TDD test for first-glance discoverability.
- Architecture, governance profile, and kernel contract tests.
- Docs quality and markdown lint.
- OpenSpec lifecycle validation for this active carrier.
- Claims, evidence freshness, report, status, and head-bound proof before land.
