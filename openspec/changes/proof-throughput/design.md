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

Integration observers now consume the existing Git topology and dirty-state
owners directly instead of collecting a complete workspace report to discard
its runtime and Lease observations. The public workspace report consumes the
same extracted topology owner. Closeout still reads fresh role, dirty state,
candidate refs, ancestry and proof; mutation and hooks still enforce exact
effect admission. A public closeout counterexample rejects any full workspace
read and checks subsequent candidate movement and untracked content.

The same release profile now uses 1,362 subprocess calls, ten source-identity
constructions and one complete workspace observation, versus 1,491, twenty and
six respectively before this repair. The sample passed in 15.47 seconds;
only the reduced work counts are attributed to the change. Seventy-two related
land, closeout, release, status and failure-boundary tests passed in 583.80
seconds with one worker. This serial regression is not the two-worker throughput
acceptance. Its owned temporary root was removed.

Index-copy experiments are rejected for implementation: after establishing
non-racy file timestamps, changing `.gitattributes` let a copied/reset index
retain CRLF bytes while fresh source observation correctly normalized LF.
Clearing assume-unchanged and skip-worktree alone is therefore insufficient.
Native index-output also locks the live index and requires same-filesystem
rename, unlike the current isolated observer. No index cache, external symlink,
filesystem-monitor weakening or permissive source-currentness fallback is
introduced. Reduce redundant consumers before optimizing the remaining exact
observation algorithm.

Explicit archived-Change compilation now checks active-carrier absence in the
selected exact tree before preparing an official OpenSpec checkout. Only an
absent carrier can select the existing fully validated archive Attestation;
restoring the same-name active Change still selects its official projection.
The official CLI availability check and expected Commitment digest remain
mandatory. No archived-directory scan or alternate parser is introduced.

An alternating before/after/after/before comparison on one real archived fixture
returned the identical Commitment digest. Per lookup, subprocesses fell from
17 to 14 and elapsed time from 0.340 seconds to approximately 0.199 seconds
(41.4 percent). It removes an inevitable failing official show plus read-tree
and checkout-index, not their authorization checks. The comparison includes
fixture cleanup but its lookup timings exclude fixture preparation; this is
not a complete-proof speedup. Raw observations are in
`throughput-archive-comparison.json`. Fifty-nine linked compilation, provenance,
selection and proof-admission tests passed with two workers in 80.62 seconds;
their owned temporary root was removed.

## Validation

### Current Cost Attribution

The September 17 refresh at `590ff2cfa` ran the same native release workload
without coverage, with coverage twice, then without coverage. Elapsed times
were 13.90, 14.65, 14.44 and 13.47 seconds; all outcomes passed with 1,362 child
calls and owned roots removed. The approximately six-percent coverage overhead
in this sample does not explain the complete-proof bottleneck. It is not a
whole-suite estimate or permission to turn coverage off.

The baseline's slowest historical-repair case now passes with coverage in 32.93
seconds. Its 2,525 product Git calls, 51 Node calls and nineteen source-identity
constructions dominate Python computation. Inclusive costs include 7.02 seconds
in update-ref and its hooks, 5.79 in Node, 3.57 in rev-parse and 3.24 in source
identity; nested spans must not be added together. Evidence is retained as
`throughput-hotspot-history-repeated.{json,pstats}`.

Fresh offline wheel construction and the complete isolated installed acceptance
passed in 173.53 seconds on that source. The following exclusive accounting is
derived from nested monotonic spans, not rounded Nox summaries. It does not
overwrite the historical full-proof remainder or constitute full proof itself.

| Installed acceptance phase | Exclusive seconds |
| --- | ---: |
| Native merge preparation, conflict, abort, replay and signed continue | 70.399 |
| Other lane bootstrap, rejected prewrite and retirement recovery | 19.972 |
| Historical signature repair and reproof | 17.289 |
| First runtime activation | 13.739 |
| Successor runtime activation | 12.675 |
| Relocation and runtime repair | 12.531 |
| Installed CLI, SDK and OpenSpec checks | 5.812 |
| Initial locked dependency and wheel installation | 5.808 |
| Host-independent command-plane checks | 5.457 |
| Both owned-tree cleanup stages | 4.010 |
| Candidate topology preparation | 1.899 |
| Adopter preparation | 1.382 |
| Immutable version check | 1.056 |
| Fresh wheel build | 0.703 |
| Other measured setup, validation and orchestration | 0.653 |
| Unattributed inter-span time | 0.142 |

`throughput-install-timeline-bound.json` retains every phase and child-command
span; its acceptance receipt records every required lifecycle stage. The entire
temporary tree, including the candidate wheel, was removed. Initial dependency
copying accounts for 4.65 seconds within installation, not the dominant cost.
An initial diagnostic runner failed to import `tools` because its script root
was the evidence directory. That failed receipt and cleanup remain preserved;
the successful runner binds the repository import root explicitly.

### Runtime Inventory Reduction

The shared runtime inventory owner repeatedly reconstructed the same directory
prefix for every child. A real installed runtime with 9,722 inventory entries
made 11,430 full relative-path computations. The owner now computes each walked
directory prefix once and composes its child names, reducing those calls to
1,708. Byte hashing, modes, junction rejection and exact internal-symlink
containment checks are unchanged. No file digest or verdict cache is added.

The alternating before/after/after/before measurements were 0.900, 0.555, 0.537
and 0.665 seconds, with exactly identical inventory mappings in all runs.
These are warm-filesystem measurements, not cold full-proof savings. Paired
profiles attribute relative-path cost of 0.630 seconds before and 0.090 after.
The distinguishing regression failed on the old owner; 53 inventory, selection
and materialization cases passed with two workers in 15.06 seconds. Internal
relative-link and location-sensitive byte assertions were consolidated rather
than removed. Product/test ELOC remain 45,289/50,000 with unchanged limits.

Next prioritize observation/compilation repeated inside one admission and the
installed native merge path. Preserve independent effects and their fresh
checks; do not collapse separate admissions or replace native journeys with
mocked success. Full-suite phase timing after these changes remains unmeasured.

The rebuilt `2853c397d` wheel passed the same complete isolated installed
acceptance in 170.14 seconds, including preparation and cleanup. Native merge
took 66.55 seconds. The 3.39-second total reduction is one before/after sample,
not a controlled claim that inventory alone explains the difference. Both runs
retain every lifecycle obligation. Raw spans and the package acceptance receipt
are in `throughput-install-after-inventory*`.

### One Evidence Observation Per Proof Query

Proof selection and archive-source validation now consume the same freshly read
canonical Attestation tuple. The proof owner reads once and passes it explicitly
through Commitment compilation to the archive owner; independent archive callers
still read their own current set. None means unobserved, while an empty tuple is
an observed empty set. No persistent cache, second selector or implicit global
context is introduced. Each subsequent proof query rereads the selected set.

The native archived-proof regression fails on the former second read. It now
verifies repeated fresh queries, retired authoring Lease, omitted intent and
withdrawn archive evidence; the latter cannot reuse a prior source acceptance.
The 116-case linked proof, compilation, archive and recovery matrix passed with
two workers in 141.64 seconds. Four follow-up cases verified equivalent
assertion consolidation. A budget check rejected 50,004 test ELOC; equivalent
assertions were consolidated to 49,998 without changing the 50,000 limit.

On one real archived fixture, alternating before/after/after/before proof queries
returned the same exact proof with 25/19/19/25 subprocesses and elapsed times of
0.262/0.227/0.235/0.270 seconds. The removed six calls are the duplicate canonical
set observation, not freshness or validation bypasses. The owned fixture was
removed; `throughput-proof-snapshot-comparison.json` retains the raw comparison.
This query improvement does not demonstrate complete-proof throughput.

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
