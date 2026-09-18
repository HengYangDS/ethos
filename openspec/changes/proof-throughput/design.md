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

### Active Acceptance Target

The September 18 user adjustment sets the first complete-proof target below
1,200 seconds. The 600-second direction remains subject to measured feasibility,
not an abandoned requirement or a claim that it is unreasonable. Historical
measurements below retain their original targets and are not current acceptance.
The subsequent explicit concurrency instruction permits faster qualified worker
counts. Two workers remain a historical comparison, not a product ceiling.
Reduce duplicated work and increase reliable parallelism together; record their
contributions separately instead of postponing one until the other is complete.

The exact `7711c673648426ce8aace0e267340e02cb593591` proof passes 35 gates,
3,802 tests with one skip, and 95.067918-percent combined line/branch coverage.
Its complete wrapper takes 1,689.755 seconds, plus a separately disclosed
18.822-second preflight. Pytest accounts for 1,465.452 seconds; installed
acceptance accounts for 169.032 seconds. Neither staged performance target is
achieved. `throughput-boundaries-breakdown.json` retains exact phases and hashes.

### Native Observation Boundary

Fresh exclusive command timing of one unchanged closeout case distinguishes
frequency from cost: official OpenSpec starts take approximately 4.36 seconds;
eight native `update-ref` calls including hooks take 3.43 seconds; forty-three
profile reads take approximately 0.21 seconds. Replacing only profile-object
reads cannot explain or remove the dominant work.

An isolated exact-content comparison qualifies native batches and Dulwich 1.2.15
on SHA-1/SHA-256 loose/packed objects, linked common directories, fresh refs and
missing/corrupt objects. Reftable opening succeeds; full reftable behavior and
native platforms are not qualified. Reopening a packed repository per read can
regress performance. No library is added: native batch reuse remains sufficient
for this experiment and object reading is not the dominant measured cost.

The selected repair batches read-only argv through the official package's
exported Commander program with awaited sequential parsing. It reuses module
loading, not command results. Python retains Change selection and acceptance
compilation; the JavaScript adapter transports argv, output and exit status only.
Governance uses one general batch and one selected-Change batch, then passes the
exact observed projection to the existing compiler. Archive effects remain on
their native single-command path. The retired single-status facade is removed.

The read-shape boundary admits only existing observations. Every frame binds an
ordinal and exact argv; malformed, reordered, truncated or incomplete results
cannot provide JSON facts. Explicit native exit preserves completed output and
marks the unexecuted tail interrupted. A timed-out observation has no current
verdict; raw transport remains evidence. The existing process owner owns the
single bounded child. This does not repair worker loss or Windows containment.

Eight official reads take approximately 0.94 seconds as independent processes
and 0.136 seconds through one import. All output bytes agree except native
validation durations. Public-plan RED observes nine Node starts; GREEN permits
at most three and rejects invalidated intent on the next call. These are bounded
observations, not a complete-proof performance claim. Receipts use
`throughput-foundation-` and `throughput-official-batch-` in the existing root.

The same 192 selected native cases pass at two/four/eight workers in
109.781/62.616/47.710 seconds including wrapper and cleanup. Four/eight include
JUnit output; two does not. Four/eight case identifiers and product/selected-test
hashes match, with no skips or failures. Eight reduces elapsed time by a further
24 percent relative to four; these are observed samples, not whole-suite estimates.
Every run retains the same test timeout and no retry.
The host reports 18 physical/logical CPUs and 128 GiB memory; resource pressure
does not justify keeping the lower count. Eight workers are selected for the next
exact full proof; other counts remain eligible after equivalent qualification.
Installed-wheel execution resolves bundled OpenSpec and the exact batch script;
three package/public cases pass, with 1.329 seconds build/install and 4.450 seconds
test execution. Temporary package and test roots are removed.

### Execution Boundaries

Throughput and parallel safety share a structural requirement: ownership and
reuse follow semantic inputs and lifetimes, not test names or process count.
The existing owners retain four distinct boundaries:

| Boundary | Owner responsibility | Acceptance |
| --- | --- | --- |
| Candidate | Build one exact candidate; its consumers and native children execute that identity. Mutable-source tests retain source mode. | Reject mixed source/package execution; include build and preparation in timings. |
| Observation | Resolve relevant facts once within an explicit observation; reuse only unchanged immutable computation. | Fresh authorization, refs, Lease, trust and source at each effect; cache removal cannot alter verdict. |
| Test | Prepare independent real prerequisites for the tested obligation. Exercise full journeys where composition is the obligation. | Preserve each original behavioral claim; no shared mutable repo, hidden mocks or dropped coverage. |
| Resource lifetime | The owner outlives fallible workers and owns admission, cancellation, descendant cleanup and temporary roots. | Worker loss, nested effects and owner loss are separate fault cases; unknown containment is not success. |

Current native profiling at `ad33fdc15` finds 682 product Git and 36 Node
invocations in one closeout-policy case, including ten source-build observations.
These are measured calls, not proof that all are redundant. The existing gate
and process owners must reduce work before widening concurrency. Neither a
global Git cache, permanent serialization nor a new workflow framework resolves
these boundaries. Framework adoption requires demonstrated replacement of
existing complexity and the same fault/authority contracts.

The bounded source/package ABBA experiment uses independent mutable fixtures,
one offline-built exact wheel and actual native child import readback. Source
runs take 13.11/12.58 seconds; package runs 11.35/11.26, with Git calls reduced
from 682 to 627. Build/install costs another 0.96 seconds. All four cases pass,
but these no-coverage samples do not predict full-suite performance. The first
probe incorrectly read staging paths after rename and is retained as an invalid
experiment, not a product failure.

The experiment exposed a real fixture identity leak: installed-parent tests
still pointed native children at the test checkout. The shared fixture now
derives code and hook declarations from the invoking `ethos` package. Native
RED distinguishes current source, alternate source and installed layout; 182
runtime/hook consumers pass at two/four/eight workers in 67.04/33.47/24.26 seconds
including cleanup. The experimental path override is not product code.
Receipts use `throughput-pinned-candidate-` and `throughput-candidate-identity-`
in the existing evidence root. Full-suite package migration, coverage mapping,
surviving-owner containment and complete proof remain unverified.

Native hook admission also loaded file-write and publication owners for every
prepared reference, even when neither capability was requested. Existing hook
dispatch now loads those owners only on their respective paths; the ref adapter
no longer imports file-write admission. Native work/topic ref probes reject the
old implementation when unrelated imports are unavailable and pass after repair.
No checks, exception handling or runtime validation are bypassed. The 226 direct
hook/admission consumers pass at two/eight workers in 105.30/34.89 seconds with
cleanup. Import-only ABBA observes 617 to 437 loaded modules and approximately
0.155 to 0.113 seconds inside the import; these are startup measurements, not a
full-proof speedup. The existing evidence root uses `throughput-hook-boundary-`.

Proof-fixture preparation unnecessarily rewrote `core.hooksPath` and left a
new worktree-local configuration file. Native Attestation-set updates already
have a no-admission hook path, so the fixture now preserves configured hooks
and exact config-file presence. Its synthetic check results project the carried
plan instead of re-reading policy per gate; production issuance still performs
its independent current-policy check. RED observes config residue and three
policy reads; GREEN preserves config and requires exactly one issuance read.
All 286 direct proof, source, integration, archive, publication and history-repair
consumers pass in 641.57 seconds, 646.14 including cleanup, with two workers.
This is a no-coverage consumer run, not a full proof or controlled speedup.
Receipts use `throughput-proof-fixture-` and `throughput-proof-checks-`.

### Original Baseline

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
mocked success. Successful complete-proof timing after these changes remains
unmeasured.

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

### Exact Full-Run Findings And Consumer Repair

The frozen `9e536969b` full run completed in 1,614.26 seconds and failed:
3,751 tests passed, fourteen failed and one skipped. Pytest took 1,569.575 seconds
(26 minutes 10 seconds), versus 1,925.089 seconds in the earlier successful
baseline. That is an observed 18.5-percent pytest reduction, not complete-proof
acceptance: coverage-floor, generated-artifacts, build, installed acceptance
and SBOM were correctly dependency-blocked after the test failure. Twenty-nine
other gates passed. The separate preceding diagnostic preflight took 17.38
seconds and is not included in the full command timer.

The content-bound timing artifact now distinguishes dependency-blocked gates
from executed checks. Unit-architecture's outer gate took 1,586.98 seconds;
pytest and its parent preparation/reporting differ by 17.41 seconds. The full
command's remaining 27.28 seconds includes prior gates and orchestration.
Concurrent gate durations are not added to that elapsed time. Raw JUnit records
21,933/22,807 covered lines and 5,968/6,562 covered branches: 95.0015 percent
combined. The coverage floor was not executed after failure; these raw counts
are not a passing proof. Owned pytest basetemp was removed automatically.

All fourteen failures were omitted migration consumers, not performance-budget
failures: thirteen compact-proof cases indexed optional timing fields and one
candidate test mocked the retired full dirty-provenance reader. The compact
projection now treats absent timing as unknown, preserving its optional artifact
contract; the candidate test consumes the current boolean dirty owner. It still
tests both dirty and stale-ancestor rejection. Sixty-nine proof-command, timing,
host-proof and candidate-boundary cases pass after repair in 14.81 seconds with
two workers. Ruff, formatting, types and unchanged source limits pass.

This exposed a concrete failure-left omission: producer timing and topology
changes had not replayed every direct CLI contract consumer. For the next
verification, the existing proof-command, remaining-landing-branches, timing
artifact and graph-runner tests are the focused consumer closure before any
full run. Do not fix missing optional fields by changing every old producer or
revive a deleted observation owner merely to satisfy an obsolete mock.

The complete per-gate and module breakdown, failed case identities and evidence
hashes are in `throughput-current-breakdown.json`. Current summed module time is
264.13 seconds for land, 169.55 for merge continuation, 152.78 for closeout,
150.22 for release and 145.59 for historical repair. These concurrent case sums
keep the priority on shared native observation and compilation. Full proof and
the 600-second requirement remain open; do not count the blocked package stages
as an improvement.

Compare the same workload before and after each repair: outcome, source/ref
postconditions, subprocess counts, elapsed time and owned-resource cleanup.
Use distinguishing counterexamples for stale inputs, mutation during reads,
corruption and isolation. Repeat representative cases before another full run.

### Current Critical Path And Observation Reuse

The latest executed command has a disjoint wall-time decomposition: pytest
1,569.575 seconds; the enclosing test gate's preparation, reporting and cleanup
17.410 seconds; work outside that gate 27.276 seconds. The last category includes
17.455 seconds before the test gate in the measured gate graph and 9.821 seconds
outside that graph interval. Those 9.821 seconds lack finer instrumentation and
must not be assigned to a guessed owner. Five dependent gates did not execute.

Concurrent prerequisite timings rank product-boundary at 12.237 seconds,
architecture-projection at 12.124, source-budget at 10.076 and module-layout at
8.391; every other executed non-test gate took less than four seconds. Their
overlap means summing them would inflate total cost. The existing machine
breakdown retains all 35 gate results, including null timings for blocked gates.
Even deleting all work outside pytest could not meet 600 seconds: test work
alone needs a further reduction of more than 61.8 percent, before allowing for
the required installed acceptance and other gates. Small lint changes are not
the critical path.

Latest summed case time is 3,110.649 seconds. CLI consumes 1,243.938; lanes
627.477; adapters 392.697; mutation 279.302; kernel 195.957; admission 185.889;
CI 90.009; all remaining families 95.380. These are disjoint concurrent case
sums, not CPU utilization or wall-time phases. Native land, closeout, release,
merge and history paths therefore remain the primary shared-owner targets.

OpenSpec governance now passes its already verified command and observed
official status to Commitment compilation. Spec-free compilation no longer
rereads that status; direct compilation still observes it, and exact-tree
compilation discards a supplied working-tree status. Malformed supplied status
is rejected rather than replaced by an optimistic reread. No persistent cache,
new parser or reusable permission is introduced.

The distinguishing native regression first observed two official command
resolutions instead of one; the repaired required-spec/spec-free and missing
context matrix passes. Ninety-eight linked compilation, governance, merge
selection and continuation tests pass with two workers in 128.93 seconds, with
owned temporary root removal. Product and test budgets remain 45,326 and 50,000.

The same covered public merge representative reduces Node calls from 40 to 36
and subprocesses from 811 to 807. Elapsed time is 16.77 seconds before versus
18.37 afterward: this sample proves less work, not a wall-time improvement.
Both preserve parents and untracked content and clean their owned roots.
`throughput-hotspot-merge-observation-reuse.{json,pstats}` retains the new
observation without overwriting the baseline. The next repair below removes
the complete governance read in merge admission followed by another in staged
prewrite. Repeated invoking source-identity construction remains open. Remove
duplicate consumers within one observation, never effect-time rechecks.

### Merge Admission Consumes Its Staged Intent Observation

Staged prewrite already resolves official intent together with exact paths,
runtime, Lease and artifact effects. It now exposes that same official report;
merge continue consumes it instead of independently reading the workspace first.
The existing resolver accepts the official reader's workspace requirement,
preserving merge's stricter requirement without changing ordinary prewrite.
Scope admission alone is insufficient: a permitted repair can still have an
invalid official intent report, which merge must reject. The selected Change
comes from the report, not an occasionally empty material-path attribution.
Incoming Change preservation and every separate effect recheck remain intact.

A real public preview, continue and repeat previously made four governance
observations. The regression now requires exactly two: one for preview and one
for effect admission. The repeated completed effect does not reread intent.
The 159-case intent, prewrite, merge and recovery matrix passes in 117.54 seconds
with two workers. Twenty-eight hook and Git-admission consumers pass in 24.84
seconds. Two targeted follow-ups cover the typed failure projection and shared
archive-authority fixture. Unknown intent and repair-versus-acceptance verdicts
remain distinguishable. All owned temporary roots were removed.

The same covered native merge sample now makes 757 subprocess calls and eighteen
Node calls, versus 807 and thirty-six after the preceding compilation repair.
Complete official governance observations fall from four to two. Measured
elapsed time is 12.59 seconds versus 18.37 in the preceding sample and 16.77 in
the earlier baseline; only the deterministic work-count reduction is attributed
to this patch. These samples include fixture setup and cleanup, but do not
establish complete-proof speed or a cold/warm distribution.

`throughput-hotspot-merge-staged-observation.{json,pstats}` retains the result.
Source identity still builds 24 times, taking 4.18 inclusive seconds in that
sample. It is now the next measured shared-owner target: expected runtime
identity and invoking runner identity must retain explicit provenance before
sharing work. Matching digests alone cannot establish that the same source
was observed. The current budget is 45,344 product / 49,987 test ELOC. Reusing
the identical authority fixture removed duplication instead of raising limits.

### Concurrency Is A Diagnostic Axis, Not A Correctness Workaround

On September 17, frozen source `bb8cc9441` ran the same 52 hook-binding,
native-supply and public-merge cases with two, four and eight workers. All three
runs passed without retries; source stayed clean and every owned fixture root
was removed. `parallel-boundary-comparison.json` records exact commands, JUnit
hashes, failures and cleanup. Coverage was disabled equally for this diagnostic;
it is not complete proof or coverage acceptance. Fixture roots were fresh, but
host/tool caches were not cleared and order was not counterbalanced.

| Workers | Whole invocation seconds | Summed case seconds | Cases passed |
| --- | ---: | ---: | ---: |
| 2 | 31.159 | 50.470 | 52 |
| 4 | 23.475 | 58.809 | 52 |
| 8 | 22.479 | 76.563 | 52 |

The sample does not reproduce a high-concurrency failure. Four to eight workers
saves only about one second while aggregate case duration grows; that suggests
interference or duplicated setup, not a demonstrated OS cause. The SCC supply
case grows from 3.847 to 9.906 seconds, but that is the whole case, not one
ten-second child timeout. Do not infer a deadline violation from those numbers.

Historical raw evidence distinguishes native startup from test assertions.
`native-hook-first-start.sample` observes a delayed child entirely in
`_dyld_start`, before Python; `integrity-retry-failures.json` preserves an SCC
fixture executable timeout. Their precise OS cause and dependence on worker
count remain unproved. Matching source/tree and empty output do not identify
a Python race, OOM, security daemon or deadlock. Existing per-worker read-only
binary supply removes repeated copies without sharing mutable repository state;
it is not proof that all native startup failures are repaired.

The permanent acceptance criterion is correct outcomes and bounded resource
ownership across supported concurrency, not a universal two-worker cap.
Keep the two-worker full-proof baseline unchanged while diagnosing the failed
boundary with native process-start/ready/exit spans, exact resource identity and
lock-owner observations. Isolate mutable fixtures by run, worker and test;
share only immutable prepared supply. Use explicit readiness instead of sleep,
short critical sections and owned process-group cleanup. Limit only a measured
scarce resource when necessary, not all tests. Preserve intentional same-resource
race tests; scheduling them away would erase the obligation. Repeated bounded
two/four/eight-worker and cold/warm verification is required before claiming
concurrency stability. No retry, exclusion, longer deadline or disabled hook
substitutes for closing the observed mechanism.

### Invoking Build Identity Is Observed Once Per Admission

The expected-build owner now returns one typed observation in place of its
anonymous identity/source pair. Its provenance distinguishes a current invoking
overlay from accepted Git objects and the legacy committed-source migration.
That distinction is necessary even when their paths or digests happen to match.
Hook observation exposes the invoking source only for the first case; runner
binding reuses its source coordinates only for that exact source root. Accepted,
explicitly supplied and foreign-source expectations still observe the actual
invoking build independently. No persistent cache, schema authority or effect
permission is added. Activation and direct readers consume the same named fields.

The native regression failed before repair with two identical source builds
inside one binding query. It now observes one, including when the caller supplies
the current hook observation, and a separate query constructs a fresh identity.
Counterexamples reject treating equal accepted/supplied coordinates or a foreign
source as invoking provenance. Existing self-hosted and pre-VERSION migration
cases keep overlay exclusion, exact accepted objects and unmodified caller index.
The 134-case runtime/hook/activation matrix passes in 47.75 seconds; 116 direct
binding, status, merge and invalid-profile consumers pass in 93.16 seconds, both
with two workers. Four fixture-consolidation follow-ups pass in 2.68 seconds.

An alternating old/new/new/old consumer comparison on one native fixture retains
identical complete binding projections. Each query uses 15/10/10/15 subprocesses
and takes 0.385/0.211/0.213/0.418 seconds. Fixture construction is outside those
query timers; cleanup is verified. Both consumers use the new producer, isolating
the duplicate consumer work. Raw evidence is
`throughput-invoking-identity-comparison.json`.

The covered public merge workload reduces source builds from 24 to thirteen
and subprocesses from 757 to 702. Inclusive source-build time falls from 4.175
to 2.342 seconds; total sample time rises from 12.59 to 13.90 seconds, with native
merge time rising from 1.32 to 3.56 seconds. This sample proves reduced work, not
whole-command improvement or resolution of the independent startup delay.
`throughput-hotspot-merge-invoking-identity.{json,pstats}` retains both limits.

No previous tuple-consumer compatibility path remains. Equivalent policy
fixtures now share the expected-build setup and use native boolean values
instead of an extra string-to-boolean translation. The 50,000-test ceiling,
500-per-file limits and 95-percent combined coverage requirement are unchanged.
Complete proof, installed acceptance and the 600-second target remain open.

### Share Proof Selection Within Each Publication Admission

The covered multi-ref publication and recovery path at `c3332a715` made 51
repository-proof selections, costing 16.812 inclusive seconds out of 41.191
seconds. Each effect admission repeated the same proof across four peer/ref
reports, release-content classification and final receipt comparison. Six
separate admission boundaries remain necessary; seven selections within each
boundary were not.

The existing publication-proof owner now reuses a supplied current observation
only for the required selection; a successful observation must also name the
exact commit. Review-only roles still require no proof. Release classification
and final push admission consume the same selection. Publication execution
shares that result across refs within one authority observation and compares it
with the carried request, deleting the independent final proof reread. The
observation is discarded at the boundary: preflight, each peer effect and each
new command select fresh evidence. Destination role, introduced commit range,
accepted closeout, source trust and remote CAS checks remain separate.

The public regression first failed with seven proof selections in one authority
observation. It now verifies one selection for dry-run and four more for each
apply or recovery command: CLI observation, preflight and both peer boundaries.
Both active-intent and no-active-intent variants pass. Removing proof after the first
peer still blocks the second; proof replacement, selection drift, unavailable
observations, same-head wrong proof, review-only publication and history repair
retain their existing counterexamples. A wrong-commit supplied proof is freshly
selected rather than reused.

The 80-case publication replay initially had 79 passes and one new comparison
failure: the test compared an internal tuple with its JSON list projection.
The assertion now uses the existing JSON normalizer; all seventeen admission
cases pass. Six affected public effect/projection cases and three final
assertion-consolidation cases pass after the budget cleanup. No test obligation
or production verdict was changed to accommodate that test representation error.
The type gate and 500-per-file limits pass; product/test ELOC are 45,373/49,999.

The same covered public workload now makes thirteen repository-proof selections,
1,955 subprocess calls and 42 Node calls, versus 51, 2,641 and 118 before.
Observed elapsed time falls from 41.191 to 30.755 seconds, a 25.3-percent sample
reduction. Inclusive proof-selection cost is 4.345 seconds. All six effect
admission boundaries still execute; they fall from 19.823 to 8.135 inclusive
seconds. Native push time increases in this sample, so work-count reduction is
the reliable attribution, not a whole-suite timing extrapolation. Raw profiles
are `throughput-hotspot-publication-{multi-ref,shared-proof}.{json,pstats}`.
All owned fixture roots were removed; no real repository peers were mutated.

Separately, the exact committed `c3332a715` wheel passed the complete isolated
installed acceptance in 166.322 seconds, including wheel construction and
cleanup, versus 170.141 seconds in the earlier measured sample. Native merge
still takes 64.358 seconds and remains dominant there. The source, wheel and
successor runtime match; the temporary root and wheel are removed. This verifies
the runtime-provenance and merge repairs in a package, not the subsequent
publication repair or a complete repository proof. Evidence is
`throughput-install-after-observation{,-acceptance}.json`.

### Consolidated Proof And Concurrency Findings

The exact `5d674a26a30f6ab1b9826090e06a29ed6c4085e8` full run blocked in
1,812.287 seconds. Pytest took 1,766.742 seconds: 3,770 passed, one failed and
one skipped. The test gate took 1,784.845 seconds including its orchestration;
these nested times are not additive. Combined line/branch coverage was
95.062400 percent. Twenty-nine prerequisite gates passed; the failed test
blocked coverage admission and all five dependent gates. The owned basetemp
was removed. The separate diagnostic preflight took 27.760 seconds and is not
included. Exact gate timing, module totals, failure, coverage and input hashes
are in `throughput-consolidated-breakdown.json` under the existing evidence root.

The failure exposed diagnostic precedence after observation reuse: missing
official tasks produced a repair-scope path gap before the original intent
failure. Merge now leaves invalid official intent to its existing decision
owner before interpreting derivative path coverage. It still rejects failed
staged admission for valid intent and preserves runtime, Lease and effect
checks. The unchanged public regression and all 55 merge/effect/continuation
cases pass in 108.75 seconds; their owned fixture root is removed. This focused
result is not a replacement full proof.

The SCC startup failure was recorded with two workers, not a demonstrated
high-worker cause. The prior two/four/eight-worker comparison did not reproduce
it. Native hook sampling showed `dyld` before Python, but did not identify its
operating-system cause. Reducing worker count is not a proven repair.

A separate isolated native probe of `ethos.adapters.process.run_command`
demonstrated that its three-second timeout killed the direct child while an
already-started descendant survived with parent PID 1. Exact diagnostic output
is `throughput-process-descendant-probe.json`; the owned descendant was stopped
and its temporary root removed. This is an executed process-ownership gap, not
proof that it caused historical pytest failures. Timeout, worker loss, inherited
pipes and cleanup must be addressed at the process owner and its test-gate
consumer. Native process groups alone do not guarantee cleanup after the
supervising worker itself is killed; platform containment and recovery need
their own falsifying tests. Do not label a POSIX-only timeout patch as complete
cross-platform supervision or add retries to hide residual processes.

The full run still exceeds 600 seconds. Prioritize the remaining repeated
native observation work and the established process-lifetime gap; retain the
same correctness bar and distinguish worker scheduling from actual subprocess
fan-out. Neither reduced call counts nor a larger worker setting proves the
end-to-end target.

### Command Interruption Boundary

The existing process owner now creates one POSIX process group per synchronous
command and terminates that group when communication raises, including timeout
and caller cancellation. It waits for its direct child and preserves the original
exception, timeout output and native checked-exit behavior. No extra supervisor
process, retry or timeout increase is introduced. Windows execution retains its
existing native behavior; Windows Job Object containment, supervisor-loss recovery
and deliberately detached descendants remain unimplemented boundaries.

All four native socket-readiness counterexamples failed before the repair:
timeout/cancellation crossed with inherited/closed output pipes left a descendant
connection open. The first repaired run exposed a test-cleanup mistake: shutdown
of an already-disconnected socket masked successful EOF observation. Closing the
owned socket fixes that test cleanup without changing its assertion. The final
173-case process, Git, runtime-source and hook consumer run passes in 46.21 seconds,
including original timeout-output preservation, text/byte stdin, environment
filtering and nonzero-exit evidence. Its owned temporary root is removed.

The file-reference matrix now declares its 34 named payload cases once instead
of repeating their names in a separate parametrization. All prior payload cases
remain; native environment cases replace duplicated mocks. Product/test ELOC
are 45,399/50,000 with unchanged limits. The native two/four/eight worker acceptance
and complete proof are not implied by this focused result.

The alternating before/after/after/before sample executes sixty native Git
version commands per variant. Elapsed seconds are 0.288/0.270/0.303/0.319 with
identical outputs. This warm microbenchmark shows no obvious startup penalty;
it does not establish complete-proof improvement. Exact source hash and timings
are in `throughput-process-group-overhead.json`. The original RED, failed test
cleanup, consumer GREEN and quality results remain in the existing evidence root.

### Scheduling-Dependent Module Identity Pollution

The four-worker replay at `ccf1276c199b914b0e393f431927961448b33079`
produced two failures among the same 173 selected cases. Both timeout tests
raised `GitExecutionError`, but their expected class was no longer the same
object: the execution-environment test reloaded the shared Git module after
other tests had imported its exception class. A serial ordered three-case
reproduction produced the same two failures. This is test-process pollution,
not evidence of CPU pressure or a pytest scheduling defect.

The import-time PATH test now imports in a fresh child with an empty PATH,
then supplies the selected Git directory and performs the native query.
It no longer reloads a shared module. Two synthetic result classes reuse the
existing completed-process fixture instead; no exception assertion, timeout,
test obligation or source budget is weakened. The ordered reproduction now
passes all three cases. A scoped audit found no other module reload in tests.

The same 173-case process/Git/runtime/hook workload then passes at two, four
and eight workers in 20.225, 11.895 and 9.908 seconds respectively. All runs use
the declared thread timeout, work stealing and no retries; their owned roots
are removed. Coverage is disabled equally for this diagnostic, host caches
are not cleared, and order is not counterbalanced. This is a bounded isolation
and scaling result, not full proof or resolution of every historical failure.
`throughput-reload-fixed-concurrency.json` binds HEAD, patch, commands and JUnit
hashes; the failed four-worker run and ordered RED remain preserved.

Separately, `throughput-worker-loss-probe.json` reproduces a real xdist worker
crash followed by a surviving command descendant. The probe releases its own
control socket and removes its temporary root afterward. The command-group
fix does not address this supervisor-loss boundary; controller-owned recovery
and native Windows qualification remain required before claiming closure.

### Shared Proof-Floor Inputs

Proof admission now asks the existing gate-policy owner for full and default
policies together. It observes the profile, registry, selected interpreter and
union of required source materials once, then compiles each floor independently.
Single-policy queries use that same owner. No persistent cache, skipped source
binding or reuse across effect admissions is introduced.

The existing proof-query regression failed with two profile reads and now
requires one per query, including the next fresh query. Both floors retain
distinct gate membership and reject missing committed source even when that
file exists in the working tree. All 92 policy, proof, adopter, CLI and
publication-admission cases pass in 72.48 seconds; their owned root is removed.
Product/test ELOC are 45,415/49,999, with unchanged limits.

On the same exact repository commit, alternating before/after/after/before
measurements take 0.211/0.103/0.103/0.194 seconds. Material reads fall from 32
to 17 and profile reads from two to one. Policy digests, nodes, source bindings
and gaps are identical. `throughput-policy-pair-comparison.json` retains the
source hash and measurements; this is not complete-proof timing.

### In-Process Command Isolation

The shared CLI test runner restored existing environment values but retained
variables introduced by a command. Native in-process invocations reproduced the
leak on normal return, `SystemExit` and an uncaught exception. These are isolated
harness counterexamples, not evidence that every historical worker failure has
this cause. Their three RED failures and focused GREEN results are retained in
`throughput-cli-isolation-{red,green}`.

The runner now uses standard-library environment and working-directory contexts
to restore the caller on every exit. One pure indexed Git-overlay projection
replaces separate mutation and restoration helpers. The fast in-process path
remains; this isolation is for sequential calls in each worker, not concurrent
thread calls that change process-global state. The final four-module consumer
matrix passes 88 cases at two, four and eight workers in 46.95, 27.78 and 23.67
seconds including command setup and cleanup. It uses the configured thread
timeout with no retries, and removes every owned root. Coverage is disabled
equally for these diagnostic runs; host caches are not reset and the four-worker
run overlaps a 1.96-second static gate, so these are not controlled speedup
estimates. Source budget, file size and product typing pass at 45,415 product
and 50,000 test ELOC. No full-proof or worker-loss completion is implied.

The refreshed covered native publication profile at `0a359fb27` passes in 38.49
seconds including profiler overhead and temporary-root cleanup. It observes
1,942 direct launches through `Popen`, including 42 Node commands. The existing
process owner accounts for 34.65 inclusive seconds, so its nested consumers must
not be added to that value. This diagnostic replaces the old `subprocess.run`
counter, which misses the new process-group executor. It supports eliminating
repeated native observation before increasing workers; it is not a whole-suite
speedup. `throughput-hotspot-publication-popen-current.{json,pstats}` contains
the exact source binding, counts and call graph.

### Peer-Set Observation

Publication requests and effects now read a peer's requested refs through one
bounded native `ls-remote` call. The single-ref consumer uses the same observer.
Present, absent, peeled-tag and unavailable results remain per-ref projections;
the native advertisement is not claimed as an atomic snapshot. Each subsequent
effect and recovery still re-observes the peer and applies exact CAS.

The public two-peer/two-ref regression failed because preview made four
advertisements instead of two. Its repaired path retains atomic per-peer
publication, failed-peer isolation, recovery and fresh proof selection. All 79
publication cases pass with two workers in 164.28 seconds; the wrapper including
cleanup takes 165.58 seconds. This focused run excludes coverage and is not full
proof. Native transport fault injection replaces a copied unavailable-report
fixture, preserving timeout details and extending coverage to duplicate, extra,
malformed and orphan-peel responses. Product ELOC falls by 27 to 45,388; test
ELOC remains 50,000. Ruff, format, type, file-size and source-budget checks pass.

`throughput-remote-batch-comparison-verified.json` compares identical native
repositories in before/after/after/before order. Fourteen refs, including an
annotated tag and absent branch, produce equal complete observations for SHA-1
and SHA-256. Direct Git launches fall from 41 to three and advertisements from
14 to one. SHA-1 samples take 0.254/0.018/0.018/0.268 seconds; SHA-256 samples
take 0.288/0.024/0.023/0.290 seconds. These are local-peer observation timings,
excluding fixture preparation, not WAN or whole-proof measurements. The first
comparison script accidentally created a SHA-1 source for its SHA-256 peer;
the native format probe identified that fixture error, and the final comparison
explicitly binds both formats. All temporary roots are removed.

### Peer-Local Effect Admission

Publication retains a complete preflight before the first effect. Each later
peer boundary now admits only that peer's destinations, while freshly checking
the common source and the request-bound proof. A review-only peer in a mixed
request still revalidates the accepted proof; narrowing the destination set
does not downgrade the request. No proof, source-trust or CAS result is reused
across effects.

The native two-peer/two-ref regression first failed with twelve destination
admissions instead of eight. It now observes four initial admissions and two
at each peer boundary, including recovery. Existing proof-selection counts are
unchanged. The combined fault matrix preserves trust, proof, policy and already
matching-peer drift cases, and adds mixed-request success and proof-loss cases.
All 81 publication tests pass in 173.53 seconds with two workers, or 175.29
seconds including wrapper preparation and cleanup. This is focused diagnostic
testing without coverage, not complete proof. Source budget, file-size, typing,
Ruff and format pass at 45,405 product and 49,999 test ELOC.

`throughput-peer-authority-comparison.json` repeats the same native request in
full/full/full versus full/peer/peer admission sequences, alternating before,
after, after, before. All three verdicts remain pass. Destination admissions
fall from twelve to eight and direct Git launches from 453 to 325. Timings are
2.604/1.825/1.819/2.497 seconds; the first sample overlaps the read-only write
admission check, so reduced work counts are stronger evidence than that timing.
These sections perform no remote writes and exclude fixture preparation.
The public effect tests separately verify real writes and partial recovery.

### Gate Process Ownership

Command gates now use the existing process executor instead of a parallel raw
subprocess path. The same socket-based native regression covers direct-command
timeout, direct cancellation and gate cancellation, each with inherited or closed
output pipes. Both new gate cases first failed because descendants kept their
sockets after cancellation. An earlier probe had an invalid canonical command
identity and did not reach execution; only the corrected admitted probe is RED
evidence. No new process framework or timeout setting is introduced.

Missing commands retain exit 127 and their exact command/root diagnostics.
Other process-creation failures retain structured evidence and are not mislabeled
as missing executables. Real native missing, permission-denied and nonzero-exit
cases replace the old raw-subprocess mock. Provider result cases share one
matrix while retaining success, failure, warning, informational and missing-verdict
assertions. Product/test ELOC is 45,403/49,992; type and size/budget gates pass.

The same 111 process/gate/architecture consumers pass at two, four and eight
workers in 5.93, 5.36 and 5.32 seconds, respectively. Wrapper times including
cleanup are 6.44, 5.88 and 5.85 seconds. All use the declared thread timeout,
no retries and equal no-coverage diagnostic settings. The two-worker sample
briefly overlaps a read-only quality check; these are correctness/scaling
observations, not a controlled speedup claim. Another 47 public proof-command
consumers pass in 14.58 seconds, or 15.03 including cleanup. Every owned test
root is removed. Receipts use the `throughput-gate-process-` prefix in the
existing evidence root.

This repair requires a living caller. The separate
`throughput-worker-loss-same-group-current.json` probe at `7b5ad8964` proves
that a descendant survives real xdist worker loss even without creating a
nested process group; the older probe also exercises group escape. The installed
pytest-timeout thread handler calls `os._exit(1)`, which cannot run caller
cleanup. Switching timeout modes, restarting workers or adding retries is not
a containment repair. Recovery must have a surviving lifetime owner and cover
worker loss, nested descendants and platform boundaries without per-command
supervisor startup or unsafe PID/name scans. This remains an open acceptance
obligation, not a result of the passing cancellation cases.

### Surviving Owner And Failure Phases

The isolated six-case `throughput-worker-owner-native-experiment.json` tests
an execution owner outside a crashing caller. Both explicit exit and SIGKILL
close same-group descendants and nested commands created through that owner,
without disturbing a concurrent healthy command. A descendant creating an
unregistered group survives in both cases. This is a throwaway feasibility
experiment, not installed containment, a trusted RPC protocol or product repair.
All experiment roots were removed. Owner death, native Windows containment,
unregistered escape and production I/O remain unproved.

Native macOS `NOTE_TRACK` registration returns errno 45, while ordinary fork/exit
notification works; it cannot supply inherited descendant tracking here.
Source inspection found process-wrap uses Unix process groups, running-process's
contained-spawn path also uses per-command Unix groups, pyreap adds a Python
watcher per command, and processkit's reviewed supervisor owns restart/backoff.
None of these inspected paths demonstrates the complete missing guarantee.
No dependency or persistent broker was installed. The existing evidence root
retains upstream source and command receipts under `throughput-supervision-`.

The prototype's cost comparison failed before producing timings: signaling an
unreaped, already-exited group returns PermissionError on this host. This is
also reproducible through the product when cancellation follows that exit.
Previously the outer OSError catch falsely labeled it process creation failure.
The existing executor now wraps only Popen creation; communication and cleanup
retain their actual errors and exception context. It shares one Popen lifetime
across platforms, including the standard Windows timeout-output drain, instead
of hiding Windows creation inside a second subprocess.run path. No permission
error is ignored, and the unresolved cleanup race is not claimed fixed.

The creation/communication distinguishing test failed before repair and passes
afterward. The same 279 process, Git, runtime, hook, gate and public proof cases
pass at two/four/eight workers in 33.30/18.78/13.50 seconds, with observed wrapper
times of 33.68/19.17/13.89 seconds. All roots were removed, source stayed frozen,
and JUnit hashes and commands are in `throughput-process-phase-concurrency.json`.
These equal no-coverage runs use the default thread timeout without retries;
native Windows execution and full proof are not covered. Product/test ELOC is
45,404/49,996; type, size and source-budget gates pass.

### Typed Attestation Set Read

The existing native object reader now accepts an exact per-object type vector.
Attestation selection batches the root commit with its member blobs, validates
the complete canonical root bytes, and retains Git's root-identity hash check.
This removes a redundant revision-to-tree process without introducing a Git
hash implementation, persistent cache or second object parser. Each read still
observes the selected ref and validates membership; CAS semantics are unchanged.

Both native hash formats first failed the reduced-work assertion. The repaired
38-case set suite passes, including cold/warm transport faults, root metadata
and digest corruption, root/member kind substitution and mismatched type counts.
One matrix replaces three repeated protocol-test setups. The 284-case shared
consumer closure passes with two workers in 353.88 seconds, or 356.82 including
wrapper cleanup. This focused no-coverage run is not complete proof.

`throughput-set-batch-comparison.json` compares identical 24-member native sets
in before/after/after/before order. Ten reads use 60/50/50/60 Git starts in both
formats. SHA-1 timings are 0.340/0.278/0.301/0.332 seconds; SHA-256 timings are
0.343/0.268/0.267/0.330 seconds. Results and original indexes remain identical;
temporary roots are removed. Fixture preparation is excluded. The first
comparison lacked the required evidence binding and failed before measurement;
the corrected fixture, not that failure, supplies the comparison. Product/test
ELOC is 45,401/49,996, with type, size and source-budget gates passing.

Final performance acceptance measures complete proof on the same workstation
with declared qualified concurrency and the locked toolchain. Include preparation and
cleanup, retain all gates and at least 95-percent combined line/branch coverage,
and report cold-computation and warm results separately. Initial installation
or network acquisition not included by the command must be disclosed separately.
The active staged target is defined above; partial speedups do not satisfy it.


### Exact Full-Proof Readback And Cancellation Race

The immutable `2acfe4a080d6c1c6f82b692d0a54144f87e179f9` proof passes all 35
gates with 3,797 passed and one skipped case. Combined line/branch coverage is
95.085528 percent. Complete elapsed time is 1,840.895 seconds, plus a separate
26.174-second preflight. The 600-second target remains unmet. Exact wall
accounting, artifact hashes and the case ranking are in
`throughput-post-batch-breakdown.json`; this unchanged proof was not rerun.

| Exclusive phase | Seconds |
| --- | ---: |
| Pytest | 1,622.028 |
| Installed acceptance | 165.104 |
| Test setup, reporting and cleanup | 18.597 |
| Prerequisite critical path | 17.246 |
| Outside the gate graph | 12.891 |
| Coverage and artifact processing | 1.081 |
| Build | 1.427 |
| SBOM | 2.522 |

A native land-policy case still makes 885 product subprocess calls, including
849 Git calls, thirteen source observations and 36 Node calls. Repeated native
work, not worker count alone, remains the primary optimization target. Native
Node compile-cache and alternative spawn experiments did not justify adoption;
`throughput-node-compile-cache-probe.json` and
`throughput-posix-spawn-comparison.json` retain their costs and limitations.

A real unreaped child establishes the cancellation-race counterexample:
communication raises the selected error after the child exits; group signaling
returns PermissionError and masks that error. The native kernel source snapshot
in `parallel-xnu-signal-official-source.stdout.log` excludes zombies from the
group callback and explains this observed boundary; upstream main is not proof
of the exact installed kernel implementation.

The existing process owner now resolves this exceptional path by polling/reaping
its exact child and observing group absence. A live child or a still-existing
or unobservable group retains the cleanup failure. Group absence alone permits
the original exception to propagate. No permission suppression, signal retry,
PID scan, timeout increase or new supervisor is introduced. Ordinary execution
adds no native call. Native regressions also cover an exited group leader with
a living descendant, so skipping cleanup after parent exit is not a solution.

`parallel-cleanup-race-red-corrected` fails only the intended error-identity
assertion before repair. The first test expansion also assumed a timeout after
both parent exit and output-pipe closure; that invalid fixture expectation was
removed rather than changing command semantics. Three observer tests share one
native-selection fixture while retaining each authority assertion; budgets stay
at 45,412 product and 50,000 test ELOC, without weakened thresholds.

`parallel-cleanup-concurrency.json` binds the source patch, exact commands and
JUnit hashes. The same 282 process/Git/runtime/hook/gate/public-proof cases pass
with two, four and eight workers in 35.98, 20.21 and 14.78 seconds including
owned-root cleanup. Source is frozen throughout, all temporary roots disappear,
and no worker restart or retry is used. These no-coverage diagnostic runs retain
host caches and are not counterbalanced; they are not full-proof or native
Windows qualification. Type, size and source-budget gates pass separately.

Worker hard-exit containment remains open: caller-side cleanup cannot survive
its own process death. The prior same-group survivor probe remains valid
counterevidence. Next repairs must preserve a surviving lifetime owner, nested
command boundaries and healthy concurrent work; no global process scan or
permanent serial test policy substitutes for that guarantee.


### Batched Native Effect Observation

The Git object owner now resolves each invocation's ordered revision set with
native `cat-file --batch-check`; effect observation and Attestation validation
consume that one result. Queries are deduplicated within the invocation, not
cached across effects. Response cardinality, type, OID spelling and ordinal
binding are validated; transport failure is not interpreted as absence. The
HEAD read remains explicit, and this batch is not an atomic Git snapshot.

Attestation validation resolves the exact immutable repository identity once
instead of repeating the same resolver inside its postcondition check. It still
checks current refs, trees, time, canonical evidence and authority separately.
The records reader no longer parses the same carried plan twice. Native CAS,
recovery and compensation remain at their existing owners.

The first reduced-work counterexample failed on per-ref observation. The native
comparison in `throughput-batch-facts-native-comparison.json` uses 32 updates and
one assertion, ten reads, and before/after/after/before ordering. Both SHA-1 and
SHA-256 need 350/20/20/350 Git starts; each result is identical after removing
its observation timestamp. Wall times are 1.632/0.102/0.109/1.466 seconds and
1.481/0.104/0.113/1.423 seconds. Fixture preparation is excluded and shared host
caches remain; this is not a full-proof speedup.

Native review exposed an important distinction: `cat-file` reports missing both
for an absent ref and for a ref whose object is gone. Both hash-format regressions
failed before repair. A missing batch row now requires exact `rev-parse` absence;
a dangling ref or unavailable observation blocks. This extra diagnostic is paid
only for missing rows, not every successful read. The 152-case final focused
suite passes in 10.72 seconds and six public closeout/signed-release cases pass
in 59.56 seconds, with owned roots removed.

Before the missing-row refinement, 190 focused cases passed in 15.64 seconds;
121 shared land, closeout, release and historical/signature-repair cases passed
in 381.69 seconds. The final missing-row refinement was verified through the
focused matrix and public consumers, not by relabeling the earlier source patch.
The old postobserve test injected failure only on a redundant second repository
read; it now injects unavailable current revision observation. Duplicate fixture
setup was consolidated with unchanged assertions and native effects. Product
and test ELOC are 45,447 and 50,000; size, type and source-budget gates pass.

The representative covered land profile reduces product process/Git calls from
885/849 to 856/820. Its elapsed time is 18.90 seconds versus the earlier 16.48;
this run overlapped another test batch and cannot support a speedup claim.
Do not sum these timings or confuse all captured subprocess calls with product
calls. The trace and raw counters are in `throughput-hotspot-land-batched-facts`.

A separate installed-wheel feasibility probe at `94e3ebffa` passes the same land
case in 14.06 seconds after a 1.29-second offline build. Its children still use
source-bound fixtures, coverage was disabled, and no matched control was run;
it does not justify whole-suite migration or a source-currentness cache.
`throughput-packaged-hotspot.json` binds the wheel to exact source/tree. The
owned wheel/install tree was removed. The 600-second complete-proof goal and
surviving-worker resource ownership remain open.


### Prepare State Without Repeating An Unrelated Workflow

The current profile spends approximately 0.04 seconds initializing the basic
repository but about four seconds executing `lane start` during preparation.
Most generic land/proof/archive fixtures require native current state, not a
repeated test of lane creation. The shared fixture is now `prepared_work_lane`:
it reuses native repository/candidate setup and `create_change_source_lane`,
selects candidate/dev explicitly, creates independent Git metadata/worktrees,
and acquires a real Lease through the existing owner. No mutable repository,
ref, Lease, receipt, verdict or source identity is shared or cached.

Public start is still exercised directly by its dedicated boundary tests, the
existing CLI start-to-dirty-land case and installed package lifecycle acceptance.
Generic preparation does not claim start Attestations exist. Consumers retain
their original proof, archive, integration, recovery and policy assertions. The
renamed fixture has no compatibility alias. One explicit base input extends the
existing lane-state fixture instead of adding another preparation implementation.

The distinguishing RED forbids invoking the CLI during generic state setup.
GREEN verifies the minimal current runtime, a real Lease and sibling isolation
across Git common directories, worktree bytes and holders. The duplicate hook
check is folded into this fixture contract and observes actual `Popen` starts,
not the superseded `subprocess.run` interception. Thirty-two fixture/start
boundary cases pass in 15.69 seconds; 272 direct consumers and archive/start
cases pass with two workers in 337.98 seconds, 339.95 including owned cleanup.
The tree remains frozen and every owned temporary root is removed.

`throughput-fixture-comparison.json` compares the same land-policy case in
before/after/after/before order. Product Git starts are 821/682/682/821; Node
starts stay at 36. Times are 21.32/16.92/15.87/16.43 seconds. The repeat controls
show host variability, so no fixed wall-time gain or whole-suite reduction is
claimed. This diagnostic disables coverage equally and substitutes only the
old fixture for its control; tested product behavior is unchanged.

Source budget, types and size pass at 45,447 product and 49,992 test ELOC.
The next exact-source complete proof must establish the unchanged 95-percent
combined coverage floor and complete elapsed time. Removing incidental repeated
coverage is not permission to omit a required behavior. The 600-second target,
worker-loss containment and accepted/runtime/publication closure remain open.

The subsequent exact `cc659470` full proof took 1,481.429 seconds and blocked:
3,798 tests passed, one failed and one skipped. Pytest took 1,438.862 seconds;
coverage, generated artifacts, build, installed acceptance and SBOM did not run
after the unit failure. This is not a complete-proof speedup measurement.
The owned pytest root was removed. The stale-effect test also fails with no
parallel workers: its synthetic plan lacked a native Git repository and patched
a symbol outside the actual observation path. Native batching therefore rejected
invalid revision input before reaching the intended stale-plan boundary.

The repair reuses the existing native Git-effect fixture, detaches HEAD after
planning without advancing the target ref, and observes the real recovery reader.
It requires one read, exact stale rejection, unchanged HEAD/refs/worktree and no
intent residue. Duplicate synthetic plan/proof builders are removed; production
admission and recovery ordering are unchanged. The module passes all 16 cases;
238 sibling ref-intent, Git-effect and process cases pass at two/four/eight workers
in 17.96/10.88/7.76 seconds including cleanup. These equal no-coverage diagnostics
neither change timeouts nor retry workers. Receipts use `throughput-ref-intent-`
under the existing evidence root. Full-proof acceptance remains unverified.

### Carrier Readiness And Coverage Source Identity

The first eight-worker full proof at `db99bb7a` took 503.505 seconds and
blocked. The sole test failure re-executed format selection: the `.mjs` adapter
had a formatter owner but the placement declaration still admitted only npm
distribution modules. The earlier preflight ran before the new module entered
Git's index, so its success did not cover the final tracked carrier set.

Use the existing JavaScript adapter owner for native package adapters and npm
distribution. Domain modules remain outside that carrier home. Declare format
selection as a test prerequisite because architecture tests consume its result;
the existing scheduler then reports blocked, unexecuted dependent checks while
independent diagnostics remain available. Freeze/stage the complete candidate
before the final cheap preflight; prior observations do not cover newly tracked
inputs. The registry/public-proof regressions verify the edge and retained
failure cause without adding a second scheduler or a fake data dependency.

Coverage was 94.954 percent, with 35 additional missed observations concentrated
in unchanged runtime materialization. A fixed two-case `pytest -n 1` replay
reproduced the cause: the supply fixture rewrote the live module's `__file__`,
and coverage cached that origin outside its source set. The subsequent real
verification ran but was not measured. Retaining the executing package source
removes this attribution mutation; the same verification lines become covered.
The fixture still distinguishes dependency/image/build sources and selected
runtime reuse. Its source-identity assertion fails under the old setup.

This does not prove the complete 95-percent floor, worker-loss containment or
installed delivery. Only a new frozen full proof can settle those execution
results. Do not change coverage configuration, merge focused data, reorder tests
to hide the problem or retry failed cases. Public `.mjs` acceptance, domain
rejection, full gate dependencies, native supply and package acceptance remain
separate checks at their existing owners.

The broad targeted run passes 280 cases at eight workers in 6.746 seconds with
an isolated coverage file and removed basetemp. The final carrier/dependency
matrix passes 53 cases, including every declared inexpensive readiness class.
Duplicate declaration-only edge tests are replaced by public proof execution;
shared carrier observation is computed once per test module, and native smoke
identity is asserted by the existing generation fixture rather than a separate
repeated setup. Every original acceptance assertion remains represented.
The 29-gate cheap preflight passes in 17.701 seconds at 45,547 product and 50,000
test ELOC. These are not complete-proof, installed or accepted-source claims.

### Same-Channel Native Metadata Observation

The Windows package journey rejected unchanged merge metadata because path stat
and descriptor stat expose different ctime semantics. The existing reader now
compares pathname snapshots to pathname snapshots and descriptor snapshots to
descriptor snapshots. Native file identity joins the two channels before content
is read. It retains ctime change detection within each channel, ignores only
read-induced atime, rejects nonregular paths/handles and both replacement
windows, and closes every opened descriptor. No platform exclusion, timestamp
exception or second metadata reader is introduced.

The stable different-channel case failed before the repair. The final owner
matrix passes fourteen cases, including descriptor/path drift and pre-open and
mid-read replacement. Sixty-seven merge/recovery/real-kill/public-continuation
cases pass at eight workers in 40.151 seconds; after test consolidation the owner
matrix was rerun. Access-time and descriptor-release assertions now live with the
same observation owner rather than duplicate lifecycle setup. Product/test ELOC
are 45,553/49,991; size, types, module boundaries and Ruff pass.

The repaired `4afaeb849` source passes all 35 full gates in 614.301 seconds with
3,825 passed, one skip and 95.084517-percent combined coverage. Test execution
uses 431.191 seconds and installed acceptance 153.207 seconds. This is a warm
locked-environment measurement, not cold provisioning or delivery elapsed time.
The proof's owned temporary root is absent. Candidate integration and both
proposal projections bind this source; accepted/runtime remain at `40bc6ff4`.

All nine GitHub native OS/Python jobs passed and their downloaded smoke artifacts
verify the selected source, package-only commands and native merge recovery.
GitLab pipeline 7364 passed. GitHub source verification was still running at the
September 18 11:31 +08 observation. Its actual command retained two workers and
300-second signal timeout through template overrides, despite the qualified
source defaults. Remove those duplicate GitHub values from the existing template
and copy projection. The distinct GitLab container override remains until its
resource envelope is qualified. The regression rejects GitHub's three stale
overrides and retains byte-equality between template and output; nine cases pass.
No running CI is interrupted, and the new projection still needs committed proof.

The rechecked worker-loss counterexample at `f6b0dd664` remains negative; no
permanent supervisor, weak PID sweep or exception conceals that separate lifetime
obligation. Native metadata acceptance does not establish descendant containment.

### Verification Failure Owns Its Unaccepted Generation

GitHub run 35301534646 finished with two fixture startup timeouts before their
intended assertions: native module version execution exceeded ten seconds in
runtime manifest and deferred-cleanup preparation. Its 3,823 passed, two failed
and one skipped cases took 3,979.389 seconds; the complete unit gate took
4,064.041 seconds. The original JUnit, coverage and hosted receipt are retained
under the existing evidence root. Owned basetemp cleanup completed. A two-case
covered replay passes in 3.623 seconds without changing product bytes; it does
not establish the hosted timeout's OS cause.

Following that exception exposed a distinct deterministic lifetime defect:
after staging is renamed, verification cleanup handled only OSError and
ValueError. TimeoutExpired and caller cancellation therefore left an unverified
named generation. The owner now cleans its newly created target on every
unsuccessful verification exit, then propagates the original exception.
A pre-existing generation is never owned by that cleanup path. The replacement
failure matrix retains the prior exit diagnostics and adds a real subprocess
timeout and caller interruption; its two new cases fail before the repair.
The owner module passes seventeen cases after repair and verifies retained
generation bytes, not only directory existence.

This closes neither the intermittent startup cause nor loss of the supervisor
itself. It introduces no timeout increase, retry, alternative activation path
or process broker. Accepted/runtime/peer delivery remains a separate observation.

### Native Scheduling Bounds Failure Drain

The existing test-gate argument owner selects native load scheduling with a
maximum scheduling chunk of one. Xdist retains its required lookahead; this is
a bounded queue, not a promise of one in-flight test. The prior worksteal mode
preallocated large worker queues, so disabling restarts still drained unrelated
work after a crash. No vendor patch, new scheduler or retry layer is introduced.

The replacement regression invokes the actual gate with an eighty-case native
collection: healthy execution runs each case once; worker loss remains nonzero,
retains the crash diagnostic, records no success and removes owned basetemp.
The prior owner fails the queue bound. Related gate consumers pass 55 cases.
Existing process and kill-after-marker helpers replace duplicated test plumbing;
all prior coverage and stale-completion assertions remain present.

The same 196 native ETHOS cases pass at eight workers under both schedulers with
identical case identifiers: worksteal takes 10.945 seconds and load takes 11.700
seconds, including scratch cleanup. This single ordered warm comparison does
not establish a healthy-throughput gain; it qualifies result equivalence while
the fault experiment demonstrates bounded drain. Full proof remains required.
Supervisor death and intermittent runtime startup stay separate open boundaries.

### Verified Supply And Executable Acceptance Have Distinct Lifetimes

The current hosted gitleaks failure occurs during its ten-second version probe,
not secret scanning. The materializer previously committed the downloaded
archive only after that probe, so an execution failure discarded already verified
input and forced the next attempt to download it again. The existing cache lock
now commits the exact digest- and member-verified archive before attempting
executable activation. Unverified downloads and failed staged executables still
leave no preparation residue; old executable bytes remain unchanged. Reuse
rechecks the archive, and a repeated bad version remains a failure without a
second download. No cache, retry layer, relaxed timeout or new authority is added.

The native failure matrix reproduces both wrong-version and real timeout loss
before the repair, alongside digest/member/link/transport rejection. Two healthy
cases later timed out in a larger focused run and passed in isolation; that is
unresolved startup evidence, not grounds to remove their assertions or certify
the host. The independent same-56-case QoS comparison takes 39.597 and 34.438
seconds normally versus 94.233 seconds under background policy. The live custom
runner differed from its installed vendor template in that policy. Passive idle
waiting could not ensure an admission gap between queued jobs. The completed
cutover instead removed only its existing custom routing label, waited for native
worker exit and remote idle, changed only ProcessType to the vendor value, then
restored the exact labels. The new listener consumed a job; hosted proof success
remains separate. No tests were cancelled and no credential or installation owner
changed.

Process identity must exclude mutable parentage: bootout reparents an orphaned
listener, so comparing the complete process row can falsely report its absence.
The post-observation caught this error. Cleanup matched PID, start time and
executable, confirmed no child job, terminated only that old instance and proved
its absence while preserving the new service. Native cleanup sampling also found
unlink/rmdir work after pytest exit; cleanup cost belongs in full-cycle timing,
not an assumed idle wait. Receipts remain under `throughput-runner-qos-` and
`throughput-runner-background-finalization-sample` in the existing evidence root.

### Executable Observation Uses The Process Owner

The native version observer used raw `subprocess.run`, unlike the established
owned-command boundary. A real ten-second verification timeout killed its direct
executable but left a ready child alive. The socket-based regression extends the
existing transport test to version verification, with immediate and delayed
startup; both verification cases fail before the repair while transport passes.

Version observation now delegates to `ethos.adapters.process.run_command` with
its existing ten-second deadline. This removes the independent raw execution
path without another retry, cache, watcher or deadline policy. Native bootstrap
and direct script consumers retain their calling environment. The 88-case supply
and process matrix passes, including cache retention, corruption, concurrency,
timeout, cancellation and original failure evidence. Every owned test root was
removed. This closes living-caller version-check cleanup only; supervisor loss,
unregistered group escape and native Windows containment remain open.

The test matrix derives prerequisite outcomes from the existing platform/image
inputs instead of redundant expected-state columns. The native command prefix
is shared; no behavioral case was removed to meet the source budget. Current
full proof and installed acceptance remain required after this bounded repair.

### Native Fixture Code And Case State

The exact source proof at `2422bc029` ran for 723.472 seconds and failed one
bootstrap prerequisite case at its existing 30-second deadline: 3,832 passed,
one failed and one skipped. Its owned basetemp was removed. Current-source
GitHub dev at `16e346b69` separately failed 22 cases, all in native supply and
hosted-receipt fixtures; both GitLab pipelines passed. Runner policy correction
therefore does not establish complete startup reliability.

An invocation-path diagnostic ran identical shell bytes: newly executable files
cost 0.412–1.180 seconds, while repeated execution of the same file cost about
0.005 seconds. Explicit interpreter execution was similarly short. The second
concurrency sample reused paths and must not be presented as a fresh-file result.
This is evidence for avoiding repeated executable creation, not attribution to
an operating-system security service or permission to weaken that service.

Bootstrap fixtures now keep immutable command code in their module-owned supply;
case-specific platform/image inputs, logs, Git state and trust remain isolated.
The existing hosted transport supplies one read-only scanner executable instead
of rebuilding identical code per case. Real shell dispatch, supply checks,
identity assertions, all outcome cases and original deadlines remain intact.
No product cache or executable-bypass path is introduced.

The same 120 supply/receipt/process cases pass at two, four and eight workers in
49.537, 37.314 and 38.276 seconds including owned cleanup. Case identities match;
coverage is disabled equally for this diagnostic. Four workers are faster on
this sample, not a reason to infer the optimal full-suite count. Whole-suite and
hosted acceptance remain required. The existing `throughput-fixture-sharing-`
receipts bind these results; the failed source proof remains failed.

### Accepted Proof Continuity And Native Failure Evidence

The real independent-release adopter reproduced three owner mismatches: the
native hook required a retired authoring Lease while preview used repository
proof; proof-set comparison confused execution context with accepted meaning;
and an existing request was compared against a newly selected proof instead of
its carried proof. Native Git stderr was then discarded behind a generic CAS
error. These are continuity defects, not reasons to repeat full proof, recreate
the authoring lane, delete prior evidence or re-sign an existing tag.

The existing proof owner validates every complete execution envelope before
comparing repository acceptance and policy. Authoring queries retain live Lease
binding. The same selector can require an exact already-carried Attestation;
absence, expiry, corruption and selected contradictions remain blocking. Release
preview, effect preparation, replay and native hooks consume that owner. The
stored request is still recompiled and compared exactly using its admitted proof,
so arbitrary request changes never become acceptable through evidence reuse.

The existing Git process exception carries native argv, cwd, stdout, stderr,
return code and plan/effect digests. Post-observation distinguishes unchanged
refs from uncertain completion. Unknown results retain effect intents; candidate
integration does not retry native rejection, and release/accepted integration
preserve the evidence. Real refusing hooks and success followed by a lost
acknowledgement or failed observer exercise recovery without repeated effects.

The first probes also corrected an overbroad hypothesis: changing only observation
time does not change canonical Facts identity. The reproduced difference is
authoring versus repository context. Tests use real lane retirement and native
active/archive proof producers rather than inventing timestamp-only differences.
Consolidation shares boundary mocks and native preparation without deleting
distinct failures. Current exact-source full proof and installed/adopter replay
remain separate acceptance boundaries.

The accepted predecessor's GitHub package jobs exposed a different supply input:
Homebrew Syft advanced to 1.52.0 while the exact repository declaration remained
1.51.1. The official stable release API and checksum-file digests agree for both
Linux architectures. Updating that existing declaration restores native SPDX 2.3
generation against the retained accepted wheel without another installation or
version exception. New-source package and hosted acceptance remain required.

### Hosted Supply Failure Left Shift

The hosted verification wrapper already owns preparation failure, prior-report
invalidation and native exit propagation. It now invokes the existing Syft
installer after scanner/budget preparation and before proof. Both Forge source
jobs consume that wrapper; no new gate, installer, version parser or provider
workflow owns the same condition. Package execution still resolves and validates
its executable in its own environment, so preparation is not cached authority
or a claim that the later effect has succeeded.

The existing native-shell failure matrix covers scanner, budget and SBOM supply.
Each failed preparation prevents proof invocation, retains its exit and stderr,
invalidates previous outputs and returns the existing hosted failure receipt.
The healthy transport verifies that SBOM preparation occurred before consuming
the exact-source command. Shared invocation code replaces duplicate test setup;
isolated supply fixtures do not certify the real installer or a hosted job.

### Hosted Fixture Code Has A Different Lifetime From Case Data

The hosted receipt matrix previously recreated executable supply code for every
case. Both exact-native shell observation and isolated fault selection remain
required, but per-case code identity is not an acceptance condition. The existing
module-scoped transport now also owns one read-only preparation executable.
Native scanner/budget preparation and SBOM preparation link to that code and
consume isolated case data through the working directory. No production supply
owner, native command dispatch, policy check or deadline changes.

A source-level identity assertion fails before reuse. The healthy and all failed
supply cases then exercise the same invocation log: success executes exactly
once; failed preparation never invokes proof. The log starts before input
validation so a broken premature invocation cannot disappear behind bad fixture
data. Failure diagnostics, previous-report invalidation, requested source and
scanner invocation remain observed through the real wrapper.

Native paired fresh/reused-file experiments and exact-path system logs explain
why avoiding repeated executable creation is useful; they do not prove every
hosted timeout has the same cause. The initial stack probe failed while copying
protected system flags; its scratch and children were removed before the corrected
byte-only experiment. Later matches passed without sampling overhead.
The 104-case native matrix and 29 cheap gates pass with unchanged budgets,
coverage policy and timeouts. Actual binary materialization, supervisor loss,
unregistered descendants and Windows remain separate acceptance obligations.

### Owned Removal Changes Only Required Permissions

Runtime generation and test-output deletion share the existing filesystem owner.
The caller supplies an exclusively owned, quiescent path; this helper grants no
ownership or permission to retire a live consumer. Directory traversal prepares
each actual directory once, only when owner permissions are missing. POSIX
deletion does not rewrite regular-file modes. Windows only repairs a read-only
regular file with one link. Root and nested links are never traversed; runtime
generation deletion retains its stronger junction and exclusive-inode admission.
Native removal failures propagate through the existing caller policy.

The previous test-output walker rewrote writable directories and each nested
directory twice; runtime removal made every regular file writable unnecessarily.
Counterexamples observe actual changed paths and retain external bytes, inode,
mode and modification time. The unified owner replaces both deletion paths;
interpreter image creation still uses its separate writable-materialization
operation because that consumer genuinely modifies files.

A callback-retry alternative added platform and retry machinery without a
measured advantage over directory preparation, so it was discarded. The final
322-case consumer family and 29 cheap gates pass, and ten root/nested permission
cases pass on each of Python 3.12.14 and 3.14.7. These observations do not establish
native Windows or hostile concurrent-writer containment. Safe quiescence remains
the caller's obligation, and platforms without no-follow chmod retain that limit.
Sealed-tree microbenchmarks do not establish whole-proof throughput or bounded
recovery after supervisor death; those existing obligations remain open.

## Reference-Preserving Archive And Stable Supply

Archive is a path transformation, not merely byte relocation. A relative
reference is interpreted against its source document; unchanged Markdown bytes
can name a different object after the document moves. The existing archive
projection owner derives the permitted destination edits from exact Git trees.
Micromark provides concrete destination spans for links, images and definitions;
all other text, code, titles, Unicode and line endings remain unchanged.
Internal Change targets move with their documents. Repository targets retain
their exact logical paths. Missing, escaping or undecodable targets are explicit
failures, including targets removed from the observed postimage.

Canonical requirements continue through the exact locked official OpenSpec
builder. It applies the original and adjusted delta against the same preimage;
ETHOS does not copy its delta parser. The existing source-binding renderer then
consumes the corrected canonical bytes. Recognition admits only native output
awaiting projection or the exact derived output, and replay is idempotent.
Arbitrary content edits and declaration drift remain rejected. Native command
failure uses the existing compensation owner, not a second transaction engine.

Git rename similarity is not authority: corrected short documents can appear as
delete/add. Their exact authorized source deletions remain attributed. A file
created and deleted within one Change can also disappear from the net baseline
diff; validated archive effect paths remain proof obligations when current scope
is nonempty. Empty repository scope does not reactivate unrelated history.

The adapter explicitly rejects HTML carrying href/src attributes, special Git
entries in the moving source, and special-entry reference targets. It does not
independently validate fragments. Supporting those reference forms and recovery
after supervisor loss remain separate obligations. Native package execution
qualifies the locked OpenSpec builder and production dependency closure.
A real package probe exposed asymmetric canonical-path comparison through a
symlinked installation parent; both coordinates now use resolved paths. A native
alias regression and packaged archive/replay/compensation distinguish that repair.
Malformed transport and timeout cannot authorize projection; timeout returns
through the existing compensation boundary. Micromark replaces spelling-based Markdown rewriting; it does not add
an authored meaning store. End-to-end verification, not a rewritten digest,
establishes acceptance.

The user-requested stable-supply refresh shares this qualification boundary:
OpenSpec 1.13.1, Prettier 3.9.8, Node 26.9.0 for declared hosted consumers, and
updated Python runtime, build and development locks. Node's Python wheel remains
24.19.0, the latest published stable wheel observed on September 18; it is a
distinct supply channel, not proof of Node 26 package execution. Filelock 4.0.0
cannot resolve with Nox's virtualenv dependency requiring filelock below 4.
Keep the compatible 3.32.7 closure until that constraint is resolved; do not
ignore dependency metadata or narrow Python support to manufacture success.
Official release/index metadata and native resolver outputs remain in the
existing evidence root. CI source templates and byte-identical projections
move together under exact patch admission, including the OCI image digest.

The isolated Filelock 4 probe passes native virtualenv contention, reentrancy,
reacquisition, environment creation, Nox execution and pre-commit configuration.
Its dependency-health check still rejects the declared virtualenv upper bound.
These observations justify further upstream compatibility review, not a full
platform claim or an installed constraint override. The probe roots are removed.

The first exact source proof at f4a169d31 passes 3,868 tests with one skip, but
combined line/branch coverage is 94.980088 percent. Build, installed acceptance
and SBOM were dependency-blocked; 593.059 seconds is not complete acceptance
latency. The owned test root is gone. Add distinguishing transport-failure and
post-effect compensation cases, then rerun exact proof without combining focused
coverage or relaxing the 95-percent threshold.

## Quality Transport And Supply Review

Five independent read-only agent reviews and a cross-examination round evaluated
architecture, supply, assurance, performance and ecosystem compatibility against
source 7f81088fe65768d56390eaca36dbc7426034ac57. Raw reports and source bindings are
retained in `build/evidence/quality/commit-integrity/quality-committee.json`.
They are design evidence, not independent execution or product acceptance.

| Alternative | Disposition and evidence |
| --- | --- |
| Retain the current native closure | Operational containment only. Filelock 3 remains an unresolved latest-stable gap; no exception or completion is inferred. |
| Remove Nox and the pre-commit framework | Not selected without capability-preserving evidence. Eight modules consume Session operations; twenty declared gates and both Forge projections use Nox. A new Session clone would transfer complexity, not remove it. |
| Separate launcher and checks with native tooling | Feasible in the isolated probe, not qualified on real consumers. Import-time project dependencies and invoking-interpreter capture remain obstacles. Filelock 3 in the launcher would still leave comprehensive freshness open. |
| Repair the upstream constraint owner | Preferred supply path: supported stable metadata and behavior, native resolution, dependency health and repository acceptance. Local overrides or relabeled rebuilt metadata do not establish upstream support. |
| Remove measured redundant work at existing owners | Selected bounded performance direction: operation-local runtime observation first, then demand-driven setup and measured lifecycle work. No full-cycle speedup is inferred from a profile. |

Nox is not a second proof scheduler. It supplies used output capture, accepted
exit codes, environment changes, positional arguments and failure behavior.
The native ETHOS hooks and optional six-check framework projection have distinct
coverage. Removing a projection requires disposition of that capability, not
an assertion that unobserved usage proves it unnecessary.

Current Filelock 4 and virtualenv's below-4 requirement have no common solution
inside one installation. A different resolver cannot change that fact. Before
the next release-acceptance decision, recheck supported upstream supply once;
if no repair exists, evaluate an obligation-preserving replacement of the
constraining owner or retain an explicit unresolved result. Waiting or another
environment does not complete freshness. No arbitrary waiting period, automatic
exception, downstream fork, or new dependency platform is admitted.

The latest proof's unit and installed-acceptance spans are sequential:
571.943 and 214.819 seconds inside an 821.599-second wrapper observation.
The separate 184.926-second installed timeline includes nested runtime, lane and
merge spans; their durations must not be summed. The measured duplicate runtime
inventory is actionable, but its profiled cumulative time is not an unprofiled
speedup estimate.

Two proposed tests were withdrawn rather than allowed to legislate a design:
blanket framework absence, and universal script-to-uv.lock/.venv binding.
The surviving obligation is semantic: declared executable/source/supply identity,
supported interpreter, fresh applicability and preserved failure behavior.
A stdlib script or native adopter tool must not acquire artificial uv requirements.

Migration experiments, if later selected, must exercise real consumers:
accepted scanner findings, redirected collection output, environment deletion,
positional arguments, missing supply and cancellation. Process-group nesting
requires an explicit native fault case: replacing ordinary Nox child launches
with independently grouped children can escape outer group cancellation.
This is a source-level risk, not a newly reproduced fault. Full native-platform,
installed-runtime, proof and cleanup evidence remain separate acceptance bars.

## Single-Observation Status

Public status observes hook/runtime currentness once and supplies that same
typed observation to workspace runner/schema binding. The existing workspace
payload carries it only inside the call; public JSON and source-binding policy
remain unchanged. Subsequent calls independently reread selector, inventory,
expected source and launcher bytes. Effects retain their own fresh admission.

The original regression observed two selected-runtime reads. The replacement
extends the existing public corruption/recovery case: all three status calls
read once, damaged package data unarms the runtime, and restored bytes recover
the original result. Missing-launcher and stale-build policy cases share setup
without conflating their distinct transport states. No quality threshold or
test obligation was removed to accommodate the hard test budget.

Five alternating fresh-process handler pairs used identical current repository
inputs. The baseline handler came from 7f81088fe, the candidate from this source.
Results were equal in every pair; native runtime inventories were two versus
one. Median handler time was 5.581587 versus 4.965634 seconds. The first baseline
sample was slower, so medians and individual samples are retained. This is not
a full-proof, cold-bootstrap or installed-successor speedup claim. Evidence is
single-status-paired-measurement.json in the existing commit-integrity root.
Focused command, hook, runtime, archive-planning and write-admission consumers
passed 197 cases; frozen exact proof and successor delivery remain required.


The first full proof at b16ad4dda failed one non-Git workspace test double:
it accepted selected_runtime but not the existing owner's forwarded hook_binding.
The failure is in the test transport, not a reproduced runtime admission defect.
The corrected double records the complete keyword observation and asserts both
values, preserving the non-Git diagnosis. Focused selection now includes
tests/unit/lanes/status in addition to imported callers and hook/runtime tests.
All imported call sites and string-based patch targets were searched before
the rerun. Coverage remained above 95 percent, but dependent package gates did
not execute; the 571.571-second failed attempt is not full-proof throughput.
