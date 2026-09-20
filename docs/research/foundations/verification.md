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

[Hypothesis][hypothesis], targeted mutation testing and real effect traces should
replace repetitive example scaffolding where they preserve or strengthen failure
sensitivity. Keep semantic scope separate from resource cost. A pure rule test
should not install a full runtime; a ref/process/lock boundary needs the real
resource. Shared fixture code and copied assertions are not independent evidence.

[Allure 3][allure3] deserves a report-only prototype against existing results,
not rejection as decoration. Its inspected release has a TypeScript implementation,
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

### September 20 Execution Lessons

These conclusions come from the current work-lane failures and bounded replays,
not a claim that the complete product or every verifier is qualified.

| Mistaken assumption | Required correction at the existing owner | Observed limit |
| --- | --- | --- |
| A curated child environment excludes ambient context | Explicit replacement semantics for isolated processes; verify absent and supplied actor/Change values through a real child | The isolation repair and focused package replay passed; the current full proof remains blocked elsewhere. |
| The selected changed files contain enough meaning for command admission | Resolve bindings against the exact postimage, including unchanged definitions and excluding deleted inputs | Public counterexamples distinguish valid aliases, new commands, changed prefixes and deleted owners; installed acceptance is pending. |
| Flattened metadata or parser success proves preserved meaning | Retain typed mappings/lists and reject duplicate or malformed headers; make consumers propagate required relation failures | Local target existence is checked; fragment correctness, external freshness and complete retrieval quality remain unproved. |
| More green tests or a faster failed run proves delivery | Bind source, complete proof, package, installed behavior and hosted publication separately; distinguish failed gates from dependency-blocked consumers | The latest 608.491-second attempt blocked; it is not a successful proof below the performance threshold. |
| Writing a rule prevents recurrence | Connect the rule to the existing gate and a falsifying consumer test | README-only navigation is implemented with tracked/untracked cases, but not yet accepted or installed. |
| A familiar formatter is the repository format owner | Read the native ownership declaration before invocation; do not reinterpret another tool's warnings as repository failures | An inappropriate Prettier run changed historical table formatting; those edits were removed and the declared Markdownlint owner passed all 1,849 selected files. |

Run the smallest affected public boundary before the expensive suite. Freeze all
identity-bearing inputs during native fixture and package execution. Reuse execution
material only while its complete inputs and applicability remain valid; never reuse
effect authorization. A failed repair must improve the causal model or be removed,
not trigger an unchanged full-suite retry. Keep progress in official Change tasks,
measured evidence in existing receipts, and reusable conclusions in their topic.

## Sources

Links identify inspected documents, not blanket endorsements. Source-level and
README observations above have different strength; repository popularity and
marketing claims were not used as evidence of comparative performance.

[hypothesis]: https://github.com/HypothesisWorks/hypothesis/blob/cd434f23be1a3598085cf096e28e6738c63b29b3/README.md
[allure3]: https://github.com/allure-framework/allure3/blob/e3bd84f644e1c58276a673f9d0ec546d2aba5855/README.md
[opentelemetry-mechanism]: https://github.com/open-telemetry/opentelemetry-specification/blob/5507eb587b3b3500ccd681e816e7c26729f38aa0/specification/overview.md
[cloudevents]: https://github.com/cloudevents/spec/blob/2ed3806b4ad8fda35813263cfefb2d73098b7655/cloudevents/spec.md
