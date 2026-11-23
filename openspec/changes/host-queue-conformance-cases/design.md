# Design

## Context

See the [proposal](proposal.md). `DeliveryPipeline.prove_host` runs the test runner over
`HOST_CASES` in one process and without a failure limit, then builds the package and proves its
install. A unit test holds that every case names a tracked file, or a function that its file
defines.

## Goals / Non-Goals

Goals:

- Every hosted platform, Windows among them, runs the host queue's lock tests in a required leg.

Non-Goals:

- The Windows suite leg's stop. DR-0021 places its triage after 0.2.0, and its cause is not read
  yet.
- Any change of the queue, and any new test.

## Decisions

1. **Whole modules, not picked functions.**
   - **Rests on:** the four modules ran in 4.0, 2.5, 3.5 and 7.2 seconds on 2026-11-24 (macOS
     arm64, one worker). The cases that hold on POSIX alone skip themselves by a marker that
     reads the platform, so a Windows leg runs what applies to it.
   - **Decision:** the list names the four files.
   - **Why not functions:** a picked list has to follow every new test of the queue, and a module
     named whole carries them.
2. **The cases join host conformance.**
   - **Rests on:** the requirement "Hosted host conformance runs in declared tiers" already
     places the Windows legs in the qualification, the schedule and the typed dispatch.
   - **Why not a session or a job of their own:** that is a new row of both pipelines for what
     the existing session already does.
3. **These four modules.** Three drive the queue with real locks: its entry, a place's lifetime
   and the admission. The fourth is the proof's own admission, which the same lane changed.

## Risks / Trade-offs

- [A case fails on Windows] -> That is the evidence this Change is for. The proposal ref gets the
  Windows legs by the typed dispatch before the full proof. A failure is read to its cause and
  repaired in this lane; where the repair is not narrow, the defect is recorded as known and the
  case is named here as left out until its repair.
- [Every leg takes longer] -> 17 seconds on macOS arm64; the hosted platforms' times are read
  from this Change's runs and written into its task.
- [A case that passes locally fails a hosted push leg for every lane] -> the four modules passed
  in the hosted suites on Linux at Python 3.12, 3.13 and 3.14, and on macOS in the full proof, at
  `3e94151ea`. macOS at Python 3.12 is first run by this Change's push.

## Proof Strategy

The unit tests of the case list pass. The proposal ref's push run and one typed dispatch with
the Windows legs run the cases on Linux, macOS and Windows. The full proof runs at the head.
