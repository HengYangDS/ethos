# Proposal

## Why

A release of 0.2.0 claims the three supported Python versions on three operating systems and two
architectures, and the test suite backs that claim for one combination only. The full proof runs
the suite on the releasing workstation, macOS arm64, and the hosted quality gates job runs it on
Linux arm64; both use the interpreter that the repository locks, Python 3.14. Host conformance at
Python 3.12 and 3.13 runs five platform cases of the suite (`HOST_CASES` in
`tools/ci/delivery/pipeline.py`), then builds and smokes the package; the rest of the suite does
not run there. The archived `rc-plan` design names "the Linux 3.12 and 3.13 suites" among what is
unproved, and DR-0021 records that the Windows suite has never run in full.

That design gives the remedy in appendix B.2 and orders it as Change 4 of appendix B.8, without a
prerequisite. DR-0021 narrows the hosts that 0.2.0 declares: Windows x64 has no journey, and its
suite runs timed without blocking. The archived `rc-scope-plan` design places this row in the
batch of 2026-11-28. The release rehearsal of the next batch reads each suite leg's verdict,
counts, coverage and time, so the legs come first.

The shipped behavior probe cannot run such a leg today. Where a repository declares its tools
through Mise, the probe runs the tests on the locked interpreter whatever interpreter started it,
and it applies the coverage carrier's floor, which a leg must not decide a second time.

## What Changes

- The behavior probe gains a leg mode. A leg runs the suite on the interpreter that started it,
  measures coverage, and decides no floor. A gate never selects the mode.
- A `suite_leg` session runs the probe as a leg within the test gate's deadline and fails when the
  leg does not pass.
- The pipeline model declares three suite legs: Linux x64 at Python 3.12 and 3.13, which
  `hosted checks` needs, and Windows x64 at Python 3.14, which may fail. They run for a batch-head
  qualification and for the drift schedule, never for a push or a pull request. Each uploads its
  JUnit and coverage reports whether it passes or fails.
- The release guide and the configuration reference say so.

Not breaking: the forge ruleset requires `hosted checks` alone, whose name does not change, and a
push runs the jobs it ran before.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: two added requirements, for the legs and for a leg's coverage, and the requirement
  `One aggregate check reports the per-push jobs`, which now needs the required suite legs.

## Impact

`src/ethos/adapters/gates/python_quality.py`, `tools/ci/sessions.py`, `.config/ci/pipeline.cue`
and the workflow generated from it, `.github/workflows/ci.yml`; three test modules and one changed
pin; `docs/guides/release-and-publication.md`, `docs/reference/configuration.md`,
`openspec/specs/quality/spec.md` through this Change's delta, and `CHANGELOG.md`. The second
forge's pipeline and the supply image do not change.

Out of scope: the release rehearsal and its receipt, which is the plan's Change 6; triage of the
Windows suite, which the plan places after 0.2.0; and a shorter test gate.
