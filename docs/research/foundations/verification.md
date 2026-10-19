---
subject: ethos:foundations-verification
role: research
state: active
relations:
  part_of: ../modern-engineering-foundations.md
  informs: ../../plans/terminal-governance-product-design.md
  constrained_by: ../../governance/product-design-contract.md
---

# Verification, Reporting And Observability

Status: active research; dated observations retain their original evidence limits.

Purpose: Evaluate falsifying tests, Allure reporting, telemetry and measurement.

See also: [Research Overview](../modern-engineering-foundations.md),
[Product Design Contract](../../governance/product-design-contract.md), and
[Terminal Plan](../../plans/terminal-governance-product-design.md).

## Verification, Reporting And Observability

### Executable Wiring Review

The September 20, 2026 review separates declaration validity, provider presence,
correct invocation, adverse-result propagation and actual effect observation.
A registry entry or trace can show selection without proving the intended check
ran. Derive obligations from existing gate contracts and inspect their actual
consumer chain; do not add a second wiring inventory as an authority.

| Mechanism                                                                                                                                                                             | Use and limit                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Pydantic strict mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/) and [extra-field refusal](https://pydantic.dev/docs/validation/latest/api/pydantic/config/) | Replace repetitive Python shape checks at the existing contract owner. A valid structure does not prove a consumer used its values. Derive required schemas from that owner rather than maintaining a second editable definition.                                                                                  |
| [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)                                                                                              | Generate interacting operation sequences and check invariants against an independent small model. Retain concrete regression traces and real effect-boundary tests; generated examples do not prove unbounded correctness.                                                                                         |
| [pluggy validation](https://pluggy.readthedocs.io/en/stable/index.html)                                                                                                               | Candidate replacement for actual multi-provider hook composition. Its pending-hook check rejects implementations without matching specifications; it does not prove every required specification has an implementation or that an implementation ran. No new plugin registry is justified for a single-owner call. |
| [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/)                                                                                                        | Candidate replacement for bespoke execution tracing, projecting existing operation identities. Correlation exposes invocation paths; trace presence, sampling or export success cannot certify authorization, policy coverage or durable effects.                                                                  |

The current bounded implementation uses the already installed Pydantic dependency
for the dependency-policy contract and native Deptry arguments for execution.
Unknown fields, malformed values, missing policy and wrong path bindings require
negative tests. Property/stateful testing, plugin composition and trace export
remain distinct adoption decisions, not implementations established by this
documentation review. Measure eliminated manual paths, missed/false admission,
first-failure latency and maintenance cost against the same workload.

[Hypothesis][hypothesis], targeted mutation testing and real effect traces should
replace repetitive example scaffolding where they preserve or strengthen failure
sensitivity. Keep semantic scope separate from resource cost. A pure rule test
should not install a full runtime; a ref/process/lock boundary needs the real
resource. Shared fixture code and copied assertions are not independent evidence.

[Allure 3][allure3] is used through its native report-only operation over existing
results, not another test execution. Its inspected release has a TypeScript implementation,
modular report plugins and human/agent-oriented views. Evaluate useful dimensions:
requirements/scenarios, steps, attachments, environments, attempts, failure
classification, history and partial execution. Allure TestOps would introduce a
separate service and management concern; it is not required to produce reports.

Keep JUnit and coverage interchange for native Forge consumers. Generate Allure
from the same actual execution results, not a second test run or a manually
maintained test inventory. Include every declared verification plane, including
setup errors, skips and incomplete/cancelled gates. Missing results must not
appear green. Open reports on both configured Forges and verify their exact source
identity; an uploaded artifact or screenshot alone is insufficient acceptance.

[OpenTelemetry][opentelemetry-mechanism] is the preferred observation substrate
to trial instead of custom tracing. Correlate intent/source/runtime, candidate
iteration, verifier attempt, command, owned resource, external effect and receipt.
Keep high-cardinality identities in suitable traces/logs rather than uncontrolled
metric labels. Export is optional and failure-bounded; secret redaction and
retention are mandatory. Telemetry loss cannot grant authority or erase the
existing effect result. [CloudEvents][cloudevents] is a candidate envelope only
when event interchange has a real consumer; it does not guarantee delivery,
ordering or exactly-once execution.

Observe queue/setup/body/teardown time, process count, bytes/inodes and cache work,
then optimize the measured bottleneck. Report first actionable failure latency,
whole-change completion time, false blocks, false passes, repeated effects,
retained useful outcomes and agent handoff cost. Test counts and ELOC alone do not
prove quality or effectiveness.

The native staged-secret check exposed a false positive before source freeze:
Gitleaks 8.30.1's Sourcegraph rule accepted any 40-hex string when a provider name
occurred in the fragment, so four authentic Git OIDs in this report were flagged.
The [upstream change](https://github.com/gitleaks/gitleaks/pull/2083) proposes the
same prefix correction but was still open at inspection. The existing native
rule now requires the provider token prefix; inherited generic credential rules
still reject unprefixed token assignments. Five executed native cases distinguish
three token forms, a legacy assignment and a non-secret Git OID. The staged source
passes without removing source hashes, suppressing findings or excluding files.

### Tool Depth Is An Executed Feedback Loop

A September 13 local-time diagnostic scanned 489 Python files from the then-dirty
`4dd2f442` worktree in 0.071 seconds with native scc 4.1.0 cognitive, unique-line
and character analysis. This is a bounded runtime observation, not a benchmark or
the official ELOC measure. Per-file cognitive leaders included Python reference
observation, OpenSpec scope, prewrite, hook activation and proof CLI. Ranking alone
does not establish a defect, duplicate behavior or safe deletion.

Native history reports were tried separately with depth 100. Both fail because
scc's pinned go-git reader rejects the repository's `worktreeConfig` extension.
Do not downgrade Git configuration for a diagnostic. The release's single reader
owner is [git_open.go](https://github.com/boyter/scc/blob/c651b07a7d3aa6e97a476380eef0f478a53719a3/processor/git_open.go).
Use native Git's bounded history or an isolated exact object view when this
question must be answered; do not add a permanent compatibility analyzer.

SCC counting remains cheap and separate from diagnostic complexity. Unique-line
ratios are lexical, change coupling is co-change rather than import/effect
causality, and generated-file detection does not establish ownership. Duplicate
files must not disappear from budget accounting via `--no-duplicates`.

Current mutmut configuration targets only the verdict module. That is not broad
mutation assurance. The graph cache reports complete September 10 metadata, but
it indexes the accepted root, not these current worktree edits; its absence of
recorded issues cannot justify deletion. Serena inspected exact worktree owners.
The preceding full JUnit result places several refresh/closeout tests at 41–51
seconds; the affected proof module also spends 14–15 seconds in several setups.
Profile fixture/setup versus behavior before replacing scheduling or adding workers.

The useful loop is native measurement, source/relationship verification, a failing
counterexample, one owner repair or deletion, and an affected public-gate result.
The present repairs followed that loop: five real RED failures and 72 affected
GREEN tests. No global performance improvement or full current proof follows.
Receipts remain under the existing ignored evidence home as
`scc-capability-audit-20260913.json`, `scc-history-boundary-20260913.json` and
`authorized-reader-recovery-4dd2/`; their compact conclusions live here, not in a
second quality-policy or feedback database.

#### October 15 Tool-Depth Qualification

The candidate uses Allure CLI 3.20.1 with allure-pytest 2.16.2; the adapter's
2.x version does not mean the report generator is Allure 2. The real four-outcome
regression preserves pass, failure, skip and setup error from one child attempt,
then rebuilds Awesome HTML and Agent queries. A feature, meaningful step and safe
JSON attachment are asserted. This is bounded reporting evidence, not a complete
repository test system or delivered runtime.

| Existing owner            | Remaining effective use and acceptance                                                                                                                                                                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Pytest / Allure           | Derive hierarchy from test responsibility; add meaningful journey steps, sanitized attachments, source/runtime/environment binding and retained native history. Compare collection with outcomes and disclose deselection, cancellation and missing results. |
| Installed delivery tests  | Exercise install, adopt, change, prove, accept, upgrade, rollback and exit across Python 3.12–3.14 and supported operating systems. A smoke test or directory name does not establish end-to-end coverage.                                                   |
| Hypothesis / mutmut       | Use generated state transitions and targeted mutations at high-risk decision and effect owners; prioritize weak assertions rather than maximizing test count.                                                                                                |
| Native timing / profiling | Separate preparation, execution, observation and cleanup; measure cold/warm, calls, transferred bytes, peak memory and scaling before changing algorithms or adding caches. Persist workload-bound regression baselines.                                     |
| OCR / Ponytail / RepoWise | Use complementary reviews for independently diagnosed gaps and deletion opportunities; bind findings to exact source and close them through consumer regressions. An index or model score is not acceptance.                                                 |

The shared Python static owner now rejects development-generation bindings in
both direct and native Nox paths, without a local adopter validator. The common
rule compiler permits configured rules to demand packaged provider checks without
copying descriptors; declared native commands retain target authority and unknown
checks still fail. These are executable reuse repairs, not broader qualification.

The October 15 Context7 request was refused for quota exhaustion. The available
RepoWise MCP did not resolve this ETHOS Work Lane; its default index belongs to
another repository. Neither result is a clean ETHOS audit. Native Allure help,
the locked package and actual tests provide narrower evidence; no service,
installer, wrapper or second policy store was added to hide these limitations.

#### Release Qualification And Review Feedback

Signed source `03392fc38` removes repeated release-source qualification inside
one publication judgment. The regression wraps the real native observers:
five provenance reads and two source validations become one of each. Every new
judgment and peer effect still checks fresh authority; no persistent cache or
timeout increase was introduced. The complete five-case catch-up, refusal,
maintenance and immutable-tag selection passes with JUnit and reportlog agreement.
This is source qualification, not full proof, installed delivery or publication.

Under the original cProfile workload, the previous attempt timed out at 120
seconds; the successor completes in 70.466 seconds including process overhead.
Native Git calls fall from 3,761 to 2,607 even though the successor executes an
extra call-count check and reaches the previously unfinished tail. This is not a
paired successful-run median or a repository-wide speed claim. Reusing one
complete source result replaces two duplicate observation paths; effect-boundary
freshness remains separate from computation reuse.

Native OCR 1.13.0 exercised Claude Opus 5.5 and GPT-6 Astra over the exact two
source files. Claude exhausted its aggregate token budget with no completed
items. Astra returned process exit zero but its manifest is partial: one source
completed, one failed for budget exhaustion. One low-priority candidate remains:
repeated tag trust observation within the same judgment. Preserve that candidate
in the existing performance work; do not postpone independent CLI delivery for
it or call either report a complete clean review. The independent source review
and Ponytail pass found no further required cut in this patch.

The durable lessons are to read terminal coverage rather than process exit or
finding count, bind a model review's scope explicitly, and use native per-group
context limits before adding review workers. A denied authoring decision must
stop its dependent write in the same checked control flow. This attempt's
missed refusal was preserved, rolled back under a new passing decision, and
reapplied only after separate fresh admission; later tests do not authorize it
retroactively. Receipts, source hashes, failed attempts and profile comparison
remain under the existing `source-delivery/tool-depth-publication-reuse-*`
evidence owner, with Git-native custody before mutable report replacement.

#### First-Time Native Release Qualification

The first-time release journey qualified accepted source three times in one
process: observation, tag preparation and final execution. The existing test
spied only one import, so its count missed two real calls. One shared spy over
both imports, reset after the earlier refused hook, reproduces `3 != 2`.
Removing only the premature preparation call yields two first-apply calls;
recovery still performs three fresh calls. Native hook processes remain separate.

Nineteen distinct cases pass: all six version/object-format/mirror journeys,
four real signer-time source/ref/policy/trust changes, tag immutability, request
recovery and maintenance proof/Lease freshness. All previous behavior assertions
remain. This is a measured computation-count reduction, not a paired latency
claim or complete proof. No cache, waiver, new abstraction or longer timeout was
added. Execution still validates signed tag identity, source, proof, policy and
exact effects before CAS. Originals are `source-delivery/tool-depth-first-release-*`.

#### Interrupted Proof And Hermetic Test Inputs

The exact `9251e2de` full attempt reached its 900-second caller deadline after
32 gates completed successfully. Its partial JUnit and Allure records agree on
3,226 outcomes, including one Linux supply-fixture failure. No complete proof
Attestation exists. A stopped attempt and successful partial cases do not qualify
installation or publication; a source fix requires fresh acceptance.

The fixture declared a temporary cache but inherited an outer persistent-cache
selector. Signed source `994a0daa` uses the existing process owner's closed
initial environment for both child commands, and declares an ambient cache in
the same regression. Its 38 affected projection and cache-selector cases pass;
production cache precedence and all original assertions remain unchanged.

Explicit child overrides are not a complete environment. Hermetic fixture
commands must select the native environment boundary; do not fix this by changing
production precedence or removing a useful outer supply cache. The one-second
assertion failure does not explain whole-run cost. Available parallel case
intervals implicate repeated release and workflow execution, not a single idle
worker; cumulative case time is not wall time or complete-suite coverage.

Preserved partial reports and the isolated RED/GREEN originals are recoverable
from non-authorizing Attestation
`195989b97aea802b126b601d529badabc2f2312f8a6e7ffcf4b1a7e97d852054`.
It binds the complete original JSON as
`custody:sha256:82582d791a4b75c7d46783b4273a4ae67ed19b385f45cc74f738d9e2d9d107f4`.
The original failure state and unmet release conditions remain preserved. Its
complete member and every encoded blob were independently checked before native
scratch retirement and again during carrier migration. Keep diagnosis, preserved
bytes and actual delivered behavior separate; retries select changed inputs, not
reassurance.

### September 20 Execution Lessons

These conclusions come from the current work-lane failures and bounded replays,
not a claim that the complete product or every verifier is qualified.

| Mistaken assumption                                                     | Required correction at the existing owner                                                                                                              | Observed limit                                                                                                                                                   |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A curated child environment excludes ambient context                    | Explicit replacement semantics for isolated processes; verify absent and supplied actor/Change values through a real child                             | The isolation repair and focused package replay passed; the current full proof remains blocked elsewhere.                                                        |
| The selected changed files contain enough meaning for command admission | Resolve bindings against the exact postimage, including unchanged definitions and excluding deleted inputs                                             | Public counterexamples distinguish valid aliases, new commands, changed prefixes and deleted owners; installed acceptance is pending.                            |
| Flattened metadata or parser success proves preserved meaning           | Retain typed mappings/lists and reject duplicate or malformed headers; make consumers propagate required relation failures                             | Local target existence is checked; fragment correctness, external freshness and complete retrieval quality remain unproved.                                      |
| More green tests or a faster failed run proves delivery                 | Bind source, complete proof, package, installed behavior and hosted publication separately; distinguish failed gates from dependency-blocked consumers | The latest 608.491-second attempt blocked; it is not a successful proof below the performance threshold.                                                         |
| Writing a rule prevents recurrence                                      | Connect the rule to the existing gate and a falsifying consumer test                                                                                   | README-only navigation is implemented with tracked/untracked cases, but not yet accepted or installed.                                                           |
| A familiar formatter is the repository format owner                     | Read the native ownership declaration before invocation; do not reinterpret another tool's warnings as repository failures                             | An inappropriate Prettier run changed historical table formatting; those edits were removed and the declared Markdownlint owner passed all 1,849 selected files. |

Run the smallest affected public boundary before the expensive suite. Freeze all
identity-bearing inputs during native fixture and package execution. Reuse execution
material only while its complete inputs and applicability remain valid; never reuse
effect authorization. A failed repair must improve the causal model or be removed,
not trigger an unchanged full-suite retry. Keep progress in official Change tasks,
measured evidence in existing receipts, and reusable conclusions in their topic.

## Code-Quality And Review Tools

Measured on October 5, 2026, for proof-throughput task 12.6. The question was
which existing or additional tools expose real defects with less repeated work,
without becoming a second semantic owner or mandatory heavyweight platform.

### Measurement Boundary

The frozen working-tree sample contains 362 present Python carriers below
`src` and `tools`, including untracked candidate files. Base commit:
`4428220db4990e3484b4275e86b6bd8596262361`; committed tree:
`99d3f68437f57b6b3c1b5fc5a61f3acc96a615e6`.
The source-manifest digest is
`ead084822e8ac62a753078d62f993e8471e151c010a6aa5ffe49d8d38695cbaf`.
This snapshot precedes the review corrections below; it is not their identity
or accepted/installed proof.

Nineteen static controls comprise seventeen determinate audit signals and two
dynamic/conditional uncertainty cases. Selected rules have different contracts:
a suspicious-call audit is not taint analysis. Findings and durations below are
sample-specific, not population precision, recall or guaranteed speedups.
Static probes were read, not executed. Mutation executed only an extracted pure
verdict owner and synthetic tests. No private-source upload, external AI review,
repository dependency change or host installation occurred.

Retained run: `quality-tool-comparison-2f8yn77j`. Its
`results/source-manifest.json`, `sample-manifest.json`, command receipts,
raw outputs, pinned sources and artifact hashes identify the exact inputs.
They remain external recovery evidence, not a runtime dependency or task ledger.

### Executed Comparison

| Tool and tested version  | Actual result                                                                                                                                                   | Disposition and limit                                                                                                                                                                    |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ruff 0.16.10             | S102/S307/S602 comparison: 0.021 s on the product sample; tested import aliases and local shadowing distinguished                                               | Retain the native owner. Its intentional exact-tree-loader `exec` finding needs contextual review, not automatic removal. These three rules were not globally enabled.                   |
| Semgrep CE 1.179.0       | Three pinned official rules: controls 1.885/1.613 s, product 3.265 s; subprocess aliases found, local/shadowed calls falsely flagged, builtin-eval alias missed | Use bounded security review only. The specific taint rule missed the interprocedural trace even when the separate call-audit rule flagged its sink. No resolver replacement.             |
| ast-grep 0.45.3          | Research structural rules: controls 0.039/0.011 s, product 0.070 s                                                                                              | Select for structural navigation and review candidates. Pattern matching does not establish binding, value flow, effects or complete parse coverage. No additional gate authority.       |
| jscpd 5.4.0              | Product 0.071/0.075 s: 98 exact and 1,471 identifier-normalized clone candidates; 280/362 carriers pass the minimum-token filter                                | Select bounded clone review, not an ELOC deletion estimate. Overlapping toy clones produce 120% reported duplication; clone sums are not unique removable lines or behavior equivalence. |
| Vulture 2.16             | Product: confidence 100 gives zero findings in 0.606 s; confidence 60 gives 285 candidates in 0.661 s, including valid hooks and public entrypoints             | Do not add a hard deletion gate. An unreachable-code control is detected, but call/registration ownership must establish whether product candidates are dead.                            |
| mutmut 3.8.0             | Same extracted verdict owner, both variants 100% line coverage: weak assertions kill 2/31 mutants, semantic assertions 31/31; 1.668/1.613 s                     | Adopt targeted mutation as a test-design/review method. This qualifies this pure owner only, not all ETHOS tests or a global mutation score.                                             |
| RepoWise 0.55.0          | Offline production code-shape health: 362 metrics and 1,330 heuristic findings in 9.350 s                                                                       | Reuse prioritization and batch context; no proof or automatic deletion. Tests were not copied, so `has_test_file=false` cannot establish missing tests.                                  |
| OCR 1.12.11 and Ponytail | Delegate review found two real audit defects; subsequent native Claude and Astra calls reviewed the semantic owner and regression                               | Retain scoped review; distinguish completed model batches below. No actionable Ponytail cut or comparative reviewer-accuracy benchmark was established.                                  |
| import-linter 2.15       | Indirect forbidden dependency RED 0.154 s; same TOML contract after repair GREEN 0.122 s                                                                        | Retain the existing architecture owner. A second architecture registry is not justified by this result.                                                                                  |
| Gitleaks 8.30.1          | Nonfunctional secret-shaped control detected with a redacted report in 0.074 s                                                                                  | Retain native secret scanning; no real credential inspection or general detection claim.                                                                                                 |
| actionlint 1.7.12        | Invalid `needs` relationship BLOCK 0.020 s; repaired control PASS 0.006 s                                                                                       | Retain native workflow semantics. Subprocess linters were disabled for this narrow test, not for product policy.                                                                         |

SCC independently counted the same frozen carriers in 0.073 s. Its code/comment
classification supplies a measurement, not proof that counted complexity is
necessary or removable.

### Parser, License And Ownership Conclusions

Semgrep returned exit zero and no parser error for an irrelevant malformed file
that its rule prefilter did not inspect. A relevant malformed file reported
`PartialParsing` but still exited zero. ast-grep recovered structural matches;
Ruff rejected invalid syntax. Scanner success and zero findings therefore cannot
certify complete syntax or semantic coverage. Missing applicable observations
remain UNKNOWN through the existing observation owner.

The tested Semgrep rules are pinned to
`a84ff9cc2453ca91d581380de4b8b3f272f6f4be`.
Their separate [Semgrep Rules License][semgrep-rules-license] allows internal use,
not redistribution or offering the rules as a service. Do not bundle them in
ETHOS or adopter packages; the engine license does not grant rule rights.
Vulture and jscpd artifact licenses and hashes are retained separately.

CodeQL 2.27.1, Semgrep Pro, Sonar, Qodana and QLTY received official-source,
license, platform and operational review, not comparative analyzer execution.
Current decision: do not add these platforms to the core. CodeQL/Pro require a
measured cross-file-flow gap plus entitled, offline and target-platform
qualification; Sonar/Qodana require unique inspection value after service/engine
cost; QLTY does not justify another installer/evaluator over existing owners.
Reconsider only against those triggers, not an indefinite pending tool list.
CrossHair, Tach and Radon are metadata candidates, not tested effectiveness.

Native source extraction separately reproduced alias, shadow, cross-scope and
program-point gaps in this working tree. This pass did not execute their public
repository-audit gate or qualify the installed reader. Keep that existing
semantic-observation obligation at its unique owner; adding spelling rules or
substituting a structural scanner would not close it.

### Native Model Review Boundary

On October 5, the user authorized OCR model calls. Native preview selected the
three supply/audit source owners from signed checkpoint `5fd0a60c`; OCR's default
path filter omitted both requested test files. The actual bounded invocation
exited 1 in 0.130 s before inference: no native model endpoint was configured.
`~/.opencodereview/config.json` was absent, and AIGW's native status declared no
OCR client. No credentials, client selections or session models were changed.

Evidence: `ocr-model-current-{scope,preview,disposition}.json` and
`ocr-model-current.{receipt.json,stderr}` in the retained comparison results.
That initial configuration failure establishes neither reviewer effectiveness
nor code quality. It is historical, not the current connection status.

Native OCR configuration subsequently added UCloud Claude Opus 5.5 and GPT-6
Astra through official setters. Both use existing AIGW credential-helper pipes;
no token was copied, session model changed, or AIGW OCR Adapter claimed. Claude
remains the default. Astra is an invocation-scoped `ucloud-astra` provider using
`openai-responses` and `gpt-6-astra`. Configuration mode remains `0600` and all
preexisting values are preserved. Credential projection identity is Account and
endpoint metadata, not authorization or automatic route synchronization.

At source `5fee868249ff640310e54346f095db3e0c9ce7e5`, independent native model
reviews covered the same three hash-bound observation/regression carriers:

| Model           | Observed execution                                                                                                                  | Coverage boundary                                                                                                                                                                       |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Claude Opus 5.5 | Connection and tool round trip PASS; three files, seven finding candidates, 54.557 s, 48,352 tokens                                 | Native test inclusion was explicitly previewed; source bytes unchanged.                                                                                                                 |
| GPT-6 Astra     | Responses and tool turns observed; observation batch completed, then Python owner and test completed in 35.959 s with 38,303 tokens | Initial 59.702 s attempt exhausted its aggregate budget and excluded tests by default. Only incomplete scope was rerun with explicit inclusion; final batch succeeded without warnings. |

These executions have different contexts and budgets; times and finding counts
are not an accuracy or speed comparison. Both models identify lexical-binding,
scope, statement-order and false-completeness gaps. Independently executed static
probes also confirm malformed `package.json` scripts crashing observation,
TOML string scripts inventing executable characters, malformed build-system
shapes crashing, and recursive YAML exceeding a two-second deadline. No probe's
subprocess or environment-read behavior was executed. Astra additionally reports
registration-only Cyclopts wiring being omitted; that candidate is unverified.

Evidence remains in the existing comparison results: `ocr-native-config.*`,
`ocr-native-model-test.*`, `ocr-semantic-model.*`, `ocr-astra-config.*`,
`ocr-astra-semantic.*`, `ocr-astra-semantic-completion.*`, preservation receipts
and `ocr-findings-reproduction.json`. Findings do not establish a repair, accepted
runtime or adopter delivery; task 10.11 retains those obligations.

### Stronger Complementary Mechanisms

The October 5 official-source refresh distinguishes analysis mechanisms, not a
single universal reviewer ranking. See `advanced-quality-official-docs.*` in the
same comparison evidence.

| Mechanism                                                                            | Suitable defect boundary                                                       | Decision and evidence limit                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [CodeQL data flow][codeql-data-flow] / [Semgrep advanced analysis][semgrep-advanced] | Cross-function/file value flow, taint and resource-use paths                   | Select an entitled bounded experiment for a demonstrated flow gap; do not add a core platform or pretend CE equivalence. Global flow costs more, library/dynamic models are incomplete, and Semgrep may fall back to single-file analysis. Record actual coverage. |
| Hypothesis / targeted mutmut                                                         | Generated state sequences, invariant counterexamples and weak assertions       | Reuse property tests and the measured mutation method: both test variants had full line coverage, but weak assertions killed 2/31 mutants versus 31/31 for semantic assertions. That result applies only to the extracted pure owner.                              |
| [CrossHair contracts][crosshair-contracts]                                           | Counterexamples to pure-function pre/postconditions through symbolic execution | A bounded experiment candidate, not measured effectiveness here. Only reachable contracted entrypoints are analyzed; time limits and unsupported effects do not become proof.                                                                                      |
| Ruff / Ty / import-linter                                                            | Native syntax, type and dependency contracts with fast fail-left feedback      | Retain existing owners; tighten applicability and semantic assertions instead of creating another architecture registry. Broad types still require design and review.                                                                                              |
| Sonar / Qodana                                                                       | Additional inspections and longitudinal quality presentation                   | Do not add to the core without unique measured findings that justify engine, service and policy-maintenance costs. Source review is not comparative execution.                                                                                                     |

RepoWise, SCC, ast-grep and clone/dead-code tools remain navigation, measurement
and candidate sources. They neither certify behavior nor authorize deletion.
AI review complements these layers; disagreement selects a falsifying test,
not majority voting or repeated whole-repository model calls.

### Real Review Closure

The independent scoped review identified two defects in the existing
`tools/ci/dependency_audit.py` owner:

- Parsed policy and its recorded hash came from different reads. Revocation
  between them could leave stale local authorization. The correction parses and
  hashes the same bytes, then freshly checks disk inputs before finalization.
- Node resolver `ValueError` skipped npm's observation. The correction emits
  npm UNKNOWN/native-execution-unavailable and preserves the complete ecosystem
  result rather than losing the receipt.

The distinguishing regressions failed before the correction. The final focused
run passed 55 tests in 2.34 s (2.785 s process wall time), with no test warnings;
Ruff checks, formatting and Ty warning-as-error checks passed. The strict release
consumer remains exercised; its existing test moved to the release owner rather
than weakening the per-file budget. See retained
`review-findings-reproduction.json`, `review-regressions-red.*` and
`review-owner-green.*`. These are candidate-source results, not a signed
checkpoint, accepted runtime, full proof, hosted CI or adopter acceptance.

### Applying Findings And Recovering Evidence

The follow-up selected 644 present candidate Python carriers from native Git
inventory. Ruff with suppressions ignored, Ruff formatting, Ty with warnings as
errors and import-boundary checks passed; SCC measured one command-observation
owner at 535 ELOC, which remains a real open simplification obligation rather
than a reason to relax its ceiling. The affected public semantic consumers passed
217 cases. These are bounded candidate observations, not complete semantic
closure, product acceptance or evidence of whole-loop speedup.

The durable method is to challenge a review finding at its public consumer,
change the unique owner and preserve valid behavior and scoped uncertainty.
Syntax success is not semantic completeness; a heuristic or model report is not
deletion authority. Review disagreement selects a falsifying example, not a
vote. The [ETHOS source quality Skill](../../../.agents/skills/ethos-quality-gate-governance/SKILL.md "source-only")
routes that procedure; the implementation and regression own behavior.

Two fresh Agents without the former session could recover product meaning and
open progress. One could not open source-integrity receipts through their old
build path. The bytes were retained in native recovery custody, not lost.
Their exact contents and hashes are now in non-authorizing Attestation
`0b5ced85312259fd8b373d6e45a3efa499417fbbef1289de666e7f0542f5391f`;
native query readback verifies both. Its bounded observation summary retains
the source inventory digest and selected command receipts. This proves
preservation and retrieval, not historical-proof currentness or deployed uptake.
The existing feedback tasks retain actual-use and accepted delivery obligations.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[hypothesis]: https://github.com/HypothesisWorks/hypothesis/blob/cd434f23be1a3598085cf096e28e6738c63b29b3/README.md
[allure3]: https://github.com/allure-framework/allure3/blob/e3bd84f644e1c58276a673f9d0ec546d2aba5855/README.md
[opentelemetry-mechanism]: https://github.com/open-telemetry/opentelemetry-specification/blob/5507eb587b3b3500ccd681e816e7c26729f38aa0/specification/overview.md
[cloudevents]: https://github.com/cloudevents/spec/blob/2ed3806b4ad8fda35813263cfefb2d73098b7655/cloudevents/spec.md
[semgrep-rules-license]: https://semgrep.dev/legal/rules-license/
[codeql-data-flow]: https://codeql.github.com/docs/writing-codeql-queries/about-data-flow-analysis/
[semgrep-advanced]: https://docs.semgrep.dev/semgrep-code/semgrep-pro-engine-intro
[crosshair-contracts]: https://crosshair.readthedocs.io/en/latest/contracts.html
