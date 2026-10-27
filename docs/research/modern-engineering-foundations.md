---
subject: ethos:modern-engineering-foundations
role: research
state: active
relations:
  informs: ../plans/terminal-governance-product-design.md
  constrained_by: ../governance/product-design-contract.md
---

# Modern Engineering Foundations

Status: active research; recommendations are not accepted implementation.

Purpose: compare foundations against the complete product mission, identify
replacement opportunities, and distinguish measured results from unresolved claims.

See also: [Product Design Contract](../governance/product-design-contract.md) and
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md).

## Question And Conclusion

Which mature foundations reduce the total cost of preserving meaning, making safe
progress, delivering a usable product and learning from actual outcomes?

The scope remains problem/value observation, research, interpretation and tradeoffs,
accepted intent, compilation, capability composition, collaboration, verification,
delivery, observed benefit, learning and exit. A compiler, graph or transaction
engine covers only part of ETHOS. This report informs the existing terminal plan;
it creates neither a second contract nor an implementation queue.

The recommended architecture is a small domain-owned trust kernel over native
repository effects, declarative constraints, replaceable execution and standard
interchange. ETHOS owns meaning and admission, not another generic installer,
parser, supervisor, dashboard or workflow platform when a qualified foundation
can replace it. A tool's cache, task state, graph, signature or report does not
acquire acceptance authority.

The existing implementation is a baseline to beat, not a preservation requirement.
Earlier dismissal of Pants or substantial redesign without a common workload was
unsupported and is withdrawn. The September 20 comparisons now show both a
beneficial reuse partition and small workloads where Pants is slower. Neither
result supports a universal engine decision.

## First-Principles Selection Frame

### Irreducible Obligations

1. Preserve accepted problems, constraints, negative requirements and intended
   benefit. Valid specification structure can still encode the wrong goal.
2. Connect consequential claims to falsifying observations and their relevant
   inputs. A successful invocation does not establish check sufficiency.
3. Separate reusable computation from currently authorized effects. Recheck
   ownership, permission and external facts at the actual effect boundary.
4. Preserve outcomes across interruption. Attempt, effect, observation and
   acknowledgement are distinct; retry cannot manufacture certainty.
5. Qualify supported delivery environments. Input identity, deterministic output
   and independent reproduction are different claims.
6. Minimize total understanding, implementation, verification, repair, delivery
   and maintenance cost. Speed cannot compensate for violated hard constraints.

### Three Relations, Not Three New Databases

The requirement/evidence relation explains why an outcome is acceptable.
The computation dependency relation identifies what must be recomputed.
The resource/effect relation determines safe concurrency and retry.

Derive them from OpenSpec, contracts, native tool inputs, Git facts and results.
Imports omit runtime data and host resources; coverage omits oracle validity;
separate worktrees may share refs or external state. Do not persist another
editable master graph merely because an engine exposes a graph API. Its internal
cache or attempt history may own execution state, never ETHOS acceptance.

### Whole-Product Comparison

Candidates are a screening map, not equally mature or qualified selections.
Their licenses, stable releases, host support and actual workload fit require
verification at the selected responsibility.

| Obligation and failure                                             | Foundations to compare                                                                                                     | Replacement and authority boundary                                                                                                                         |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lost intent, wrong interpretation or missing benefit feedback      | Official OpenSpec customization, Inspect AI, DSPy                                                                          | Use source constraints and falsifying examples; capability evaluation improves interpretation, but only accepted meaning enters deterministic compilation. |
| Repeated computation or missed invalidation                        | Pants, Bazel, Buck2/DICE                                                                                                   | Replace selected scheduling, dependency inference, sandboxes and reuse; an opaque whole-suite wrapper is not incremental execution.                        |
| Repeated container setup or divergent CI recipes                   | Dagger, native BuildKit                                                                                                    | Replace container assembly and provider execution duplication; Linux execution does not qualify native macOS/Windows behavior.                             |
| Missing native/build inputs or irreproducible artifacts            | Nix/uv2nix, uv, mise, Pixi, reproducible-builds practices, diffoscope                                                      | One owner assembles each environment; derive language inputs from their lock and retire replaced provisioning.                                             |
| Contradictory declarations or guards                               | CUE, native typed models and schema generation, CEL; Cedar for a distinct relationship-authorization need                  | One editable owner per rule; compile projections rather than maintain equivalent CUE/Python/JSON rules independently.                                      |
| Names mistaken for bindings or unknown flow                        | Compiler/LSP metadata, LibCST, Tree-sitter, SCIP, CodeQL, Semgrep, abstract interpretation and graph algorithms            | Replace corresponding spelling heuristics; distinguish syntax, binding, flow and effects and report unsupported observations.                              |
| Invalid transition composition, deadlock or stale-owner acceptance | Native Git object/ref/worktree mechanisms, TLA+/TLC or Quint, Hypothesis stateful testing                                  | Replay critical model counterexamples through public behavior; preserve multiple contributions, zero/one winners, all-drop and useful results.             |
| Weak test oracle or incomplete protocol                            | Hypothesis, mutation testing, native conformance; Schemathesis for actual OpenAPI/GraphQL surfaces                         | Expose defects missed by examples; do not fabricate a transport to justify a tool.                                                                         |
| Duplicate effects or orphan execution                              | Native CAS/idempotency, structured concurrency, AnyIO, statecharts; Temporal/Restate/DBOS for genuinely durable operations | Replace duplicated lifetime/attempt handling; current authorization and resource-specific commit semantics remain outside replay.                          |
| Artifact origin confused with correctness or update safety         | in-toto/DSSE/SLSA, TUF, CycloneDX and ecosystem vulnerability tools                                                        | Standardize provenance/update verification; signatures, SBOMs and attestations do not independently prove correctness.                                     |
| Missing diagnostics or reruns only to rebuild reports              | OpenTelemetry, JUnit/SARIF, Allure 3, CloudEvents                                                                          | Derive views from actual results; preserve attempts, partial failure and redaction. Sampling cannot erase required evidence.                               |
| Formation or customization lost during adoption/upgrade            | Copier, official templates and Skills                                                                                      | Generate candidates, preserve three-way upgrade inputs and domain layout, and qualify conflict, handoff and exit without another intent store.             |
| Agent coupling or excessive plugin privilege                       | Python entry points, pluggy, MCP/A2A, WASI for demonstrated isolation needs                                                | Replace transport boilerplate with small capability contracts; discovery and invocation are not authorization.                                             |
| Unusable human/agent knowledge navigation                          | Diataxis, OKF, native API/schema generation                                                                                | Organize by reader need and semantic owner; projections do not become another intent or evidence store.                                                    |
| Unsuitable implementation language or poor UX/DX                   | Existing Python CLI/typed SDKs/Rich; Rust, Go, TypeScript                                                                  | Choose by bounded responsibility and measured total cost, not displacement of Python ELOC into another language.                                           |

## Replacement Decision

Compare repair, consolidation, replacement and deletion against the same required
behavior. Count migration, adapter code, cache/storage, supply, recovery and
ongoing maintenance, not only execution time. Existing code and sunk effort are
not benefits. When a replacement wins, migrate necessary semantics and retire its
incumbent in the same bounded sequence; retain compatibility only for a real,
tested external obligation.

Use a qualified foundation deeply within its adopted scope: native dependency
inference, explicit resources, compatible batching, invalidation, process limits,
diagnostics and result projection should replace equivalent custom machinery.
A thin command wrapper leaving the old machinery underneath is not adoption.
Conversely, enabling every optional feature is not a goal: unused services,
overlapping schedulers and duplicate policy add cost without product benefit.

Every proposal names the invariant, existing owner, minimal counterexample,
replacement interface, removed path, trust boundary, migration/recovery route,
cold/warm/invalidated behavior, platform evidence and total maintenance cost.
Make a scoped decision after the bounded comparison; do not require one tool to
replace the whole product or postpone delivery behind indefinite experiments.

### Measured Direction — September 20, 2026

The [execution study](foundations/execution.md) binds unchanged ETHOS tests to
source `06bf5cc44405bb6572e3b33d1e798538bfe1d543`, fixed dependencies and explicit
resources. It records raw output, supply preparation, invalidation and cleanup.

| Executed scope                                  | Existing pytest median | Pants warm median | Finding                                                                                                    |
| ----------------------------------------------- | ---------------------: | ----------------: | ---------------------------------------------------------------------------------------------------------- |
| 48 decision tests                               |                1.096 s |           2.080 s | No latency benefit for this small partition.                                                               |
| Those tests plus five native Git-worktree cases |                1.780 s |           1.960 s | Correct execution, still no measured latency benefit.                                                      |
| 23 public proof/source-boundary tests           |                8.540 s |           2.039 s | Useful unchanged-result reuse; first Pants execution is 14.417 s, result-store-cleared execution 27.562 s. |

The last result is not a whole-proof speedup. Its shared Node supply is explicitly
fingerprinted and verified but remains outside the Pants sandbox; those limits
must be resolved before production reuse. Incorrect source observation, invalid
pytest configuration and unavailable declared supply invalidate the passing
result and fail. Cleared-cache execution passes without a cache hit.

Pants merits the dependency-complete test-partition replacement cut, not blanket
activation or rejection. Dagger has a bounded executed container/cache/failure
probe, not package-delivery qualification. Nix/uv2nix has source-level build-closure
evidence, not an executed ETHOS build. Bazel/Buck2 remain alternatives, not
comparative winners. Follow the existing plan and Changes for actual cutover.

## Read By Question

The [foundation topic entrance](foundations/README.md) routes each question to
its detailed comparison, observations, and source references. This overview
owns only the comparative frame and common workload.

## Comparative Acceptance Workload

Execute through the existing terminal plan and bounded official Changes.
Only one selected production owner survives a successful comparison.

| Workload                          | Distinguishing observation                                                                                                                                                    |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Meaning and semantic extraction   | Preserve legal/illegal/UNKNOWN distinctions under aliases, schema errors, rule changes and contradictory combined constraints.                                                |
| Focused and complete verification | Cold, warm, source/rule/toolchain/environment-change and cleared-cache results agree; actual avoided work and first-failure latency are measured.                             |
| Native effects and cancellation   | Real CAS, stale Lease, busy resources, timeout, child death and lost ACK do not duplicate destruction or orphan resources.                                                    |
| Preparation and activation        | Exact package, prior trust, offline supply, rollback, crash recovery and bounded cleanup work on supported native hosts.                                                      |
| Reports and observability         | Rebuild views without rerunning tests; preserve all attempts, bindings, partial failure and redaction; measure storage/runtime cost.                                          |
| Collaboration and adoption        | Greenfield/brownfield paths, customization, multiple contributions, zero/one winner, all-drop, useful-result retention and conflict-aware upgrade/handoff/exit remain usable. |
| Delivery and outcome              | Zero/one/multiple remotes, exact objects, partial publication and recovery; later observations change evidence applicability without rewriting history.                       |

Hold worker counts and required behavior fixed for each comparison; qualify
higher concurrency separately. Report representative repetitions and dispersion,
setup costs, subprocesses and materialized bytes, not one selected warm number.
Cache stability does not prove determinism: clear result reuse, vary irrelevant
paths/time/locale and compare required artifact bytes. Explain intentionally
variable fields instead of normalizing away meaningful differences.

Quality completeness includes tracked-carrier scope, rule sufficiency, invocation,
failure propagation, effect admission, recovery, portability and comprehension.
A complete input graph does not validate its test oracle. No speed score offsets
missing obligations, and no benchmark claim precedes its measurement.

## Evidence And Limits

### October 9 Computation And Native-Effect Findings

Immutable semantic values should retain unchanged leaves and parents; only changed
ancestors need reconstruction. The `PythonInvocations.resolve_value` experiment
preserved complete observation multisets in four alternating same-input runs:
operation medians fell from 16.646 to 15.655 seconds and wrapper medians from
18.663 to 17.698 seconds. Allocation profiling recorded 1,676,731 to 1,266,490
`replace` calls, but profiling elapsed time increased; it is not speedup evidence.
The measured workload had zero concrete requests. These results qualify only
that observation scope, not a full-proof breakthrough. A separate substitution
shortcut passed 210 focused cases but alternating paired times were
9.233/10.565/8.933/10.998 seconds, with identical complete observations and
unchanged inputs. Opposite pair directions do not establish a stable benefit;
the shortcut and its experiment-only identity cases were withdrawn without
altering preceding admitted work. Preserve the failed hypothesis, not its code.

The broader `substitute` copy-on-change candidate retained unchanged structural
channels after resolving every current dependency. Seven RED cases passed;
180 selected cases and 435 additional existing semantic/public-observation cases
passed without repeating the first selection. Six alternating observations preserved
complete results and source hashes: median 11.590 to 8.097 seconds. Calls to
`substitute` remained 403,025, while `_replace` calls fell from 1,267,569 to 880,724.
The candidate, never an installed or full-proof performance claim, was withdrawn
with the call-time engine on 2026-10-12 (`b18465bb0`). Its workload had zero
concrete requests.

Repeated transitive summary instantiation and effect interpretation remain the
larger opportunity. Compare demand/delta worklists and context-complete reuse
before adopting another LRU or incremental framework. Pure computation reuse must
preserve binding ownership, consumed heap members, source sites and UNKNOWN;
leases, ref admission, external observations and effects remain fresh.

Evidence reuse follows exact selected case identities and consumed inputs, not
JUnit `classname` presence or a count alone. The configured discovery report has
empty class names but already contains all 24 functions and 77 parameterized
cases. A mistaken coverage lookup repeated those cases; retain that attempt as
an execution error, not new progress. Unchanged semantic bytes retain the 180
and 435-case qualification; later trust or record changes do not turn it into
new-HEAD full proof. Native scc, Ruff and Ty qualify the coherent source slice;
fresh source/effect admission and installed behavior remain separate duties.

The native held-ref repair also exposed a false abstraction: Git `verify` reports
old-to-zero hook tuples without deleting a ref. Existing native same-value
`update`/`prepare`/`abort` retains all ref locks without committing or moving refs;
the original hook still rejects real deletion. Signed maintenance `f3526386`
qualifies the actual AIGW materialization/replay without a new intent store.
Preserve native stderr rather than guessing that every preparation failure means
stale input. Model independent competing callers with separate native processes;
in-process tests intentionally share cancellation ownership.

The publication range owner was reopening native trust inputs per commit although
its verifier already accepts 128-object batches. Signed maintenance `edd40436`
reuses that capability, preserving every subject, identity and signature-format
check. Four original 558-object observations, B/C/C/B, match the complete original
report: median 91.436 to 54.295 seconds; native verification calls 558 to 5 and
trust-input reads 1,116 to 2. Both pair directions improve; dispersion remains.
Failed batches locate objects under the same pinned inputs. Original refusal,
diagnostic timeout and global trust changes cannot be erased by successful retries
or partial attribution. Three RED cases pass within 129 native cases; private
extraction and failure-evidence follow-ups pass 12 and 8 selected cases, without
repeating unchanged evidence. Only two production members and build identity
change in the exact wheel; one offline build reuses supply by reference and
releases its owned source. Actual AIGW installation selects runtime `325347fc`
with those exact signed bytes, preserving three worktrees' refs, indexes and
reflogs. Its previously failing GitHub-only publication passes in 205.075 seconds,
with push exit zero and exact remote commit/tree readback. The internal
120-second deadline is unchanged and successful GitLab is not replayed. This
closes the concrete downstream failure, not full-product proof, CI or release.

Reuse unchanged evidence by exact inputs, rerun only diagnosed changed cases,
build once from signed source with existing supply by reference, and render reports
from the same attempt. Retain failed receipts and retire completed owned scratch.
Raw comparison and maintenance receipts are in the existing bound recovery scope,
`semantic-demand-closure-20261009/{identity-sharing,substitution-copy-on-change,candidate-native-hook,commit-range-native-batch}-*`;
`proof-throughput` task 13.4.2 held their implementation and acceptance state. It
moved to `publication-history-repair`, which was archived with that task withdrawn
by DR-0016.

The original September 12 source review used official documentation and read-only
GitHub APIs; its receipts remain in the existing ignored evidence home under
`build/evidence/quality/evidence-retirement/foundations-*.json`. These historical
observations are retained for provenance, not current implementation status; the
authoring commit `4dd2f442` and its tree are no longer present in the repository:

| Historical observation           | Evidence and original limitation                                                                                                                                                                                                                                                         |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authoring and accepted baselines | Authoring `4dd2f442eb6cae9477d8599ca990d708820d0a8c`, tree `d03c47380c7e9612e1e6b8df7069a754c5588b6e`; accepted `f99627cdcfe0a4e6dc8c4ee5b00aad7b79c59277`, tree `c1d155b35f0efe43a624d5d6684a0ddedf69fb5f`. Dirty handoff work and an unrelated browser output were not research-owned. |
| Available tools                  | mise 2026.9.5, Pixi 0.80.0, Dagger 0.21.9 and Git 2.55.0 answered version queries; that did not prove integration.                                                                                                                                                                       |
| Native reference hook            | A 0.331-second isolated valid/rejected-update probe preserved old refs and config; its scratch was removed. Not a security proof or incumbent migration acceptance.                                                                                                                      |
| Scheduler and process path       | Dependency-ready scheduling and work stealing already existed. The then-observed timeout gap was not proof of the historical hang cause; it is not a claim about today's process owner.                                                                                                  |
| Budget change                    | Product/test 41,407/43,172 were below independent 50,000 limits; 74 budget tests passed in 3.15 seconds. This was focused evidence, not delivery.                                                                                                                                        |
| Framework comparison             | No common benchmark existed in that original review. September 20 execution evidence supersedes that limitation only for its named scopes.                                                                                                                                               |

September 20 receipts were recorded under `build/evidence/quality/commit-integrity/`:
`foundation-first-principles-source-check.json`, the execution study's named
Pants/Dagger records, and `foundation-source-review.json` /
`foundation-resolver-review.json`. They held successful and failed retrievals,
raw hashes, native help and execution limits; apart from the Pants reproduction
inputs that the execution study cites from custody, they are no longer retained.
Upstream snapshots and popularity are not stable-release or comparative-performance
evidence.

### Primary Sources

- [Bazel hermeticity](https://bazel.build/basics/hermeticity): input isolation and its limits.
- [Buck2 dynamic dependencies](https://buck2.build/docs/rule_authors/dynamic_dependencies/): execution-derived dependency construction.
- [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html): interacting generated action sequences.
- [TLA+ tools](https://lamport.azurewebsites.net/tla/tools.html): model checking and proof tools.
- [CodeQL data flow](https://codeql.github.com/docs/writing-codeql-queries/about-data-flow-analysis/): binding/flow scope and analysis limits.
- [Temporal activities](https://docs.temporal.io/activity-definition): idempotency despite durable orchestration.
- [Reproducible-builds definition](https://reproducible-builds.org/docs/definition/): bit-identical declared artifacts.
- [diffoscope](https://diffoscope.org/): diagnosis of artifact differences.
- [SLSA verification](https://slsa.dev/spec/v1.2/verifying-artifacts): provenance against explicit expectations.
- [TUF security](https://theupdateframework.io/docs/security/): update-specific attacks.
- [OpenTelemetry sampling](https://opentelemetry.io/docs/concepts/sampling/): sampled telemetry versus complete required evidence.

These sources support mechanism distinctions, not an ETHOS acceptance claim.
Reject framework accumulation, parallel authority, container-as-native proof,
cache-as-authorization, report-as-proof, automatic acceptance of generated
projections and ELOC displacement. Preserve the complete product scope while
retiring the superseded implementation.
