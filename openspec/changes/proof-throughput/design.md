## Context

Raw baseline, JUnit, cProfile and native Git Trace2 observations live in the
existing ignored `build/evidence/quality/commit-integrity/` evidence root.
The canonical terminal plan owns the wider P5 sequence. This Change implements
only measured throughput improvements and their correctness boundaries.

## Decisions

1. Measure complete elapsed time separately from summed concurrent case time
   and nested cumulative function time. Missing phase instrumentation remains
   unknown, not an invented allocation.
2. Prioritize shared native observation paths used by the slowest tests. A
   cheap lint speedup cannot solve the 88.6-percent pytest bottleneck.
3. Preserve fresh mutable ref, source, Lease and trust observation at each
   effect. Pure computation may reuse exact immutable inputs; LRU eviction
   cannot establish validity. Avoid a generic cache around arbitrary Git calls.
4. Reduce repeated preparation and IPC through existing native mechanisms and
   explicit operation-local values. Do not replace native acceptance tests
   with mocks or share mutable repositories between cases.
5. Keep immutable runtime inventory and corruption rejection. A faster source
   observation must include unstaged, staged, untracked, mode and index-flag
   changes and preserve the caller's index.
6. Separate native startup delay from execution. Sampling overhead and cold
   executable preparation remain visible. No automatic retries or timeout
   increases conceal failures.
7. Record execution-relative start offsets and monotonic elapsed time in the
   existing gate result, CLI and content-addressed proof artifact. A dependency
   block or dry run has null timing, not zero-cost executed evidence. Historical
   artifacts without timing remain readable; negative, non-finite and nonnumeric
   durations are invalid. Timing is diagnostic and never admission authority.

## Measured Baseline And Priority

The exact source proof at `26405d4d8f57d48f6d6a1603d738b06a688fcd7f`
passed 35 gates. `throughput-baseline-breakdown.json` contains all 35 gate
observations, every test module, source hashes and the profile comparisons.

| Layer | Measurement | Interpretation |
| --- | --- | --- |
| Whole command | 2,171.662 seconds | Includes command preparation and cleanup |
| Pytest | 1,925.089 seconds, 88.6 percent | Primary wall-time bottleneck |
| Remaining work | 246.573 seconds | Installation, other gates and orchestration; exact historical subphases unavailable |
| Installed acceptance | Approximately three minutes in Nox | Rounded, not an exact timer |
| Projection prerequisite | Approximately ten seconds in Nox | Repeats 69 projection cases later included in full pytest |
| Summed test durations | 3,808.545 seconds | Concurrent case time, not command wall time |

The summed test duration divided by two workers and pytest wall time is 98.9
percent. This is occupancy evidence, not CPU utilization. It argues against
idle scheduling being the dominant suite cost; calls may still be waiting on
native children, locks or I/O.

| Test family | Cases | Summed seconds | Share of summed time |
| --- | --- | --- | --- |
| CLI | 487 | 1,787.107 | 46.92 percent |
| Lane lifecycle and retirement | 536 | 663.070 | 17.41 percent |
| Repository and other adapters | 826 | 400.561 | 10.52 percent |
| Mutation | 239 | 374.018 | 9.82 percent |
| Kernel | 328 | 200.587 | 5.27 percent |
| Admission | 298 | 194.239 | 5.10 percent |
| Architecture | 143 | 43.352 | 1.14 percent |
| Projection | 69 | 13.744 | 0.36 percent |

These disjoint families do not exhaust the suite; the machine breakdown retains
all remaining modules. CLI, lanes and mutation together account for 74.1 percent.
The largest individual modules are land (328.772 seconds), release (267.539),
closeout (254.679), history repair (219.574) and merge continuation (173.298).

Priority follows shared work, not test filename size:

1. Reduce native calls on acceptance, release and proof selection paths. The
   representative release uses 1,610 subprocess calls, including 536 rev-parse,
   155 config, 152 show and 109 cat-file calls. Fresh reads remain necessary;
   existence probes before successful exact reads and validation of irrelevant
   effects do not.
2. Remove redundant source-overlay construction within a clearly bounded
   observation. Twenty constructions cost 5.284 seconds in the original sample.
   A copy/reset prototype reduced one current-tree observation to about 0.08
   seconds, but naive index reuse hid assume-unchanged and skip-worktree edits.
   It is not an accepted implementation or permission to trust stale stat data.
3. Resolve native startup separately. Trace2 observed an initial preparing hook
   of 19.025 seconds; sampling found dyld before Python. A later link contrast
   measured a first owned hardlink start of 3.538 seconds and subsequent starts
   near 0.03 seconds. External symlinks are outside the immutable runtime closure
   and are not an admissible workaround. No platform security setting is changed.
4. Decompose installed acceptance after the dominant test work. Keep native
   installation, upgrade, handoff, merge and retirement coverage. Then remove
   repeated projection execution without dropping failure-left admission or
   branch coverage. Saving ten seconds alone does not meet the target.

## First Implemented Reductions

Accepted-closeout selection filters exact transition/ref/head/assertion before
repository-backed validation, while still canonically validating the entire
selected set and fully validating matching candidates. The distinguishing matrix
failed before repair; 83 related tests passed afterward.

The Attestation-set reader directly observes the exact selected ref and performs
repository/existence diagnostics only on failed observation. Symbolic refs,
invalid repositories, corrupt members, ambiguous effects, concurrent CAS and
SHA-256 repositories remain governed by the existing tests. A successful set
read uses five owner Git calls instead of seven, plus the existing batch object
read. No persistent cache or second selector is introduced.

In repeated profiles of the same native release case, total subprocess counts
were 1,610 before, 1,589 after exact-effect selection, and 1,491 after ref-query
consolidation: 119 fewer calls, or 7.4 percent. Wall times were 36.36, 17.13 and
20.59 seconds respectively. Startup and host variance prevent attributing those
wall-time differences to the patch or extrapolating them to the full suite.
Both updated cases passed and their owned temporary roots were removed.

## Validation

Compare the same workload before and after each repair: outcome, source/ref
postconditions, subprocess counts, elapsed time and owned-resource cleanup.
Use distinguishing counterexamples for stale inputs, mutation during reads,
corruption and isolation. Repeat representative cases before another full run.

Final performance acceptance measures complete proof on the same workstation
with two workers and the declared locked toolchain. Include preparation and
cleanup, retain all gates and at least 95-percent combined line/branch coverage,
and report cold-computation and warm results separately. Initial installation
or network acquisition not included by the command must be disclosed separately.
The target is at most 600 seconds; partial speedups do not satisfy it.
