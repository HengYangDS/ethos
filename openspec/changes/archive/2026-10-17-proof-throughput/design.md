# Design

## Context

This Change measured and shortened the complete repository proof, which took
2,171.66 seconds with two workers at `26405d4d8`, and closed the reproduced
assurance, archive, supply and documentation-authority gaps found on the way.
It grew to 200 tasks. Its 137 completed tasks are implemented on the accepted
line; its open tasks continue verbatim in the successor Changes named in
`tasks.md`.

The full execution design, measurements and per-defect decisions remain at
signed source `7b457b27e33ad9846d15394db149d4cb7133821f` in this file's
history, and the cited receipts remain with their Attestation and Git owners.
This design keeps only the decisions that still govern the accepted
specifications and the successor work.

## Goals / Non-Goals

**Goals:**

- A complete repository proof, including preparation, every required gate and
  cleanup, within 900 seconds, with 600 seconds as the measured direction.
- Unchanged assurance: every behavioral obligation, native effect and the
  coverage floor remain required.

**Non-Goals:**

- Cached verdicts, narrower assurance, automatic retries or longer timeouts as
  a substitute for less work.
- A generic cache around arbitrary Git calls, a second verifier, or another
  persistent authority.

## Decisions

- **Measure before optimizing.** Complete elapsed time, summed concurrent case
  time and nested cumulative function time are distinct quantities. Missing
  phase instrumentation stays unknown rather than allocated. Per-gate monotonic
  timing is diagnostic and never admission authority.
- **Keep every mutable observation fresh.** Ref, source, Lease, trust and Git
  configuration are reobserved at each effect. Only complete-input pure
  decoding may be reused; reuse of native Git answers was measured, reviewed
  and rejected, because a cached success hides later object loss, configuration
  change and environment change.
- **Remove repeated work at its semantic owner.** Batch fresh native reads at
  call sites, share exact immutable inputs within one operation, and remove
  circular prerequisites, repeated judgments and pass-through wrappers. A new
  facade is not simplification.
- **Preserve native test isolation.** Shared preparation may reduce cold work,
  for example hash-checked bytecode compiled once per run, but cases never
  share mutable repositories and native acceptance tests are not replaced by
  mocks.
- **Treat quality as falsifiable obligations.** Requirements stay in official
  OpenSpec, the gate registry compiles their executable owners, native tool
  policy owns diagnostics, and CI, reports and merge controls consume the
  results without becoming another authority. A claim is accepted only when its
  required check set is complete, bound to the claimed source and policy,
  successful, and accompanied by its required artifacts.
- **Partition CI by semantic and resource boundaries.** Each job owns real
  execution or exact artifact validation, and final admission conjoins every
  required outcome. Restoring every historical job and a monolithic run with
  forwarding jobs were both rejected.
- **Archive completion consumes the existing postimage proof owner.** Archive
  evidence proves the ref and carrier transformation, not the quality of the
  resulting source.
- **Split instead of extending.** When this Change outgrew one readable,
  provable unit, its open tasks moved with their identities, states and
  acceptance conditions into focused successor Changes, and no task was
  completed by archiving it.

## Risks / Trade-offs

- [Host contention, from concurrent proofs and local CI virtual machines, times
  out tests with thin headroom] → Observation Attestation `3be1c72d` records a
  failure of this kind. Contended admission is task 9.4 of `proof-critical-path`.
- [The sustained proof p90 remained above 900 seconds over eight runs] → Task
  1.9 is closed against its five-run condition; `proof-critical-path` owns the
  remaining distribution work.
- [Accepted requirements whose implementation tasks are still open] → Each
  open task is carried by a successor Change that cannot archive until it
  completes.
