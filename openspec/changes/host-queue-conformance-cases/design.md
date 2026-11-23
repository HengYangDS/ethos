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
- Any change of the queue, and any new test. Three existing cases change what they read from
  the host, not what they assert of the product.

## Decisions

1. **Whole modules, not picked functions.**
   - **Rests on:** the modules ran in 4.0, 2.5 and 3.5 seconds on 2026-11-24 (macOS arm64, one
     worker), and the proof's module in 7.2. The cases that hold on POSIX alone skip themselves
     by a marker that reads the platform, so a Windows leg runs what applies to it.
   - **Decision:** the list names whole files.
   - **Why not functions:** a picked list has to follow every new test of the queue, and a module
     named whole carries them.
2. **The cases join host conformance.**
   - **Rests on:** the requirement "Hosted host conformance runs in declared tiers" already
     places the Windows legs in the qualification, the schedule and the typed dispatch.
   - **Why not a session or a job of their own:** that is a new row of both pipelines for what
     the existing session already does.
3. **Three modules, and the fourth left out by name.** Three drive the queue with real locks:
   its entry, a place's lifetime and the admission. The fourth, `test_proof_slot.py`, is the
   proof's own admission.
   - **Rests on:** the Windows legs of run 45247591995 at `da4227508`. On Windows x64 with
     Python 3.13 and 3.14 and on Windows arm64 the session ended in the ten-minute limit of one
     case of `test_proof_slot.py`: a `git` child that a fixture started (`init` on two hosts,
     `commit` on one) never returned its output. The cases differ (the tenth and the
     thirty-second of the module); each follows a case whose admission ended by an exception. On
     Windows x64 with Python 3.12 the same session passed whole: 119 passed, 11 skipped in 26.2
     seconds, the proof's module among them. So the stop is intermittent. No case of the three
     queue modules failed on any of the four hosts.
   - **Decision:** the list holds the three queue modules. `test_proof_slot.py` joins when its
     Windows stop is understood.
   - **Why not keep it and mark the cases:** the stop moves between cases, so no marker names it.
4. **A case does not read the runner.**
   - **Rests on:** a model review of the list named three cases, and a probe that shows a test a
     host of three CPUs without a load reading failed them before the repair: four parameter sets
     of two tests. The third, the holder state, differs only where the platform is not POSIX and
     is first shown by the Windows legs.
   - **Decision:** the load test patches `getloadavg` without requiring the name, so it runs
     where the host has none. The two worker-cap cases set the CPU count that the queue reads to
     eight; one of them expected a caller's count of three to be the smaller, which holds only
     above four CPUs, and a hosted macOS runner has three. The waiting event's holder state is
     `present` on POSIX and empty elsewhere, as `holder_state` answers.
   - **Why not a POSIX marker on them:** each asserts behaviour that Windows has too; a marker
     would drop that evidence.
5. **An assertion that a result names no path holds on every platform.**
   - **Rests on:** the closing review of decision 4's repair. For the path `C:\Users\runner\busy`
     inside a JSON text, the plain path is not a substring and the path as JSON writes it is.
   - **Decision:** the four assertions of this shape in the tests compare the JSON form. On POSIX
     both forms are the same text.

## Risks / Trade-offs

- [The probe is not Windows] -> It removes one reading and changes one count; path, signal and
  lock differences are shown only by the Windows legs.
- [A path written with forward slashes on Windows] -> The four assertions of decision 5 look for
  the path as `str` gives it. A result that carried the `as_posix` form of a Windows path would
  pass them on a Windows leg. The POSIX legs see it: there both forms are one text, and the code
  that writes a path is the same on every platform. A second needle was not added: it is the
  third form of one assertion, and a leak that only Windows makes in that form has no known source.
- [A case fails on Windows] -> That is the evidence this Change is for. The proposal ref gets the
  Windows legs by the typed dispatch before the full proof. It happened: see decision 3. The
  stop was read to its place and not to its cause, so the module is left out by name and the
  cause is a follow-up of its own; the second run of the Windows legs shows whether the three
  modules alone end.
- [The same stop appears in the three modules later] -> They start `git` children by the same
  fixture. None stopped on four hosts; a stop in a qualification would hold a release head, and
  is then read with the follow-up's evidence.
- [Every leg takes longer] -> 17 seconds on macOS arm64; the hosted platforms' times are read
  from this Change's runs and written into its task.
- [A case that passes locally fails a hosted push leg for every lane] -> the four modules passed
  in the hosted suites on Linux at Python 3.12, 3.13 and 3.14, and on macOS in the full proof, at
  `3e94151ea`. macOS at Python 3.12 is first run by this Change's push.

## Proof Strategy

The unit tests of the case list pass. The proposal ref's push run and one typed dispatch with
the Windows legs run the cases on Linux, macOS and Windows. The full proof runs at the head.
