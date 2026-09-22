# Quality Gate Design

Use this reference when strengthening ETHOS quality gates without turning CI,
hooks, or tool configuration into a second truth center.

## Gate Owner Model

A gate is active only when its existing owner surfaces agree:

1. `system/gates.toml` owns gate identity, profile, execution, evidence, and
   proof-floor membership.
2. Tool identity and policy live under the smallest stable native owner, usually
   `.config/checks/<concern>/` or a root-native file when the tool requires root
   discovery.
3. The shared gate executor owns dependency scheduling and prerequisite outcomes.
   ETHOS uses Nox for its Python checks; adopters keep their native declared
   toolchain. Local CI selects that full closure, not a private session list or
   a required Python orchestration layer. `tools/ci/scripts/` retains necessary
   platform adapters.
4. Hosted CI and hooks invoke Nox sessions, retained adapters, or ETHOS command surfaces; they do
   not restate policy inline.
5. Tests or proof commands assert the contract so drift becomes visible.

If a required relation is missing, repair its existing owner rather than add a
second catalog, registry, or wrapper.

## Quality Coverage And Evidence

Treat the complete assurance chain as the unit of review: requirement and risk,
one check owner, meaningful carrier scope, an independently selected fault,
enforced result, exact source/policy identity and one actionable repair.
Inventory existing effective checks before deleting or merging their execution.
Do not equate tool availability, graph coverage, lint success or a high coverage
percentage with correct behavior or complete product assurance.

A result must remain adverse through normalization, artifact storage, issuance,
replay and final admission, not only through its first runner. Exercise a claimed
pass with nonzero exit, warnings and unmet conditions at the actual issuance
boundary. Use the shared execution-success predicate; do not recreate Boolean
success checks in each projection. Native structured diagnostics and strict tool
flags replace prose matching. Informational output is not a warning, and missing
or malformed required diagnostics cannot certify success.

For source-derived quality contracts, resolve required checks to their original
propositions, scope, observation and rejection conditions before trusting a
report. Undefined IDs are an input defect, not an invitation for a consumer to
invent their meaning. Declaration validity, source judgment, independent
source-to-artifact review, rendered measurements and owner acceptance remain
distinct. Reference the existing contract; do not copy its checklist into a
skill. A partial presentation or export preserves every necessary condition of
the relations it expresses without pretending to cover the whole product.
Hidden content and a prior PASS cannot repair an unsupported current claim.

- `system/gates.toml` selects default and full closures. Default remains offline
  source verification. Full and local CI additionally execute declared security,
  carrier and delivery checks, including owners with explicit network needs.
  Missing required supply or external knowledge is not a passing observation.
- Native Ruff lint/format, Ty, import-linter, dependency hygiene, test/coverage,
  carrier syntax, structural invariants and security retain distinct properties.
  Review native rules against real faults and remove overlapping custom checks;
  do not enable every rule or add another quality platform mechanically.
- The existing coverage policy requires at least 95 percent combined Python
  line-and-branch evidence. Product/test source ceilings remain independent.
  No exclusions, metric changes, weakened thresholds or deleted behavioral
  obligations may compensate for a failing requirement.
- Failed or unknown prerequisite results block dependent checks without executing
  them. Independent diagnostics can continue. Package creation depends on passing
  coverage; a successful process cannot substitute for a complete result set.
- Before selecting a gate as inexpensive, inspect its transitive dependencies in
  the current registry. A focused selection is not necessarily a small workload.
  Carry the declared resource envelope into every native process explicitly;
  separate shell invocations do not inherit an earlier invocation's exports.
  Read back the actual child command and retain one live operation handle. Never
  run the same heavy closure twice merely because its top-level gate name differs.
- Local CI retains the exact command/policy, source overlay, individual results,
  stdout/stderr and a failure receipt. It never claims hosted success or repository
  proof from that fallback receipt. Use exact committed full proof for acceptance.
- Hosted observation is a separately requested read after publication, never a
  dry-run success or a self-wait inside the pipeline being observed.
- Platform qualification runs the complete declared native tool graph against
  realistic input volume. Installed tools, one passing command or a partial
  suite do not qualify the platform. Prefer native stdin/response-file interfaces
  for bounded invocation; keep one owner across platforms rather than OS-specific
  omission lists. Exact-source qualification does not automatically transfer to
  a later commit or prove release and installation.
  Shipped manifests need real-input checks with prerequisites arriving separately;
  keep executable, configuration and home roles distinct, preserve explicit user
  selection, and do not equate platform-path probes with native execution.

## Root Configuration Boundary

Keep tool policy under its semantic configuration concern when native loading
preserves direct, hook, CI and editor behavior. Root discovery files may contain
native references and irreducible path bindings, never a second rule set.
Ruff rules live in `.config/checks/ruff/ruff.toml`; root `ruff.toml` owns only
inheritance and the repository-relative cache location. Pytest is invoked with
its explicit `.config/checks/pytest/pytest.toml` owner. Verify relative paths
through each native discovery mode before claiming a configuration move safe.
Update skill package digests whenever included guidance changes.

## Learning And Failure Placement

For a reproduced failure, distinguish the observation from its causal hypothesis
and identify the violated invariant. Exercise the smallest real counterexample,
repair its existing semantic owner, remove the replaced path, and replay both
valid and invalid consumers. Use the existing Change for scope and acceptance,
the canonical plan for unresolved work, and exact receipts for results. Add a
Decision Record only for irreducible cross-Change rationale; do not add a feedback
ledger, lesson catalog, alternate rule registry or a copied adopter gate.

Select focused verification from the changed semantic owner and every consumer
of its inputs, outputs and invariants, not just touched files or similarly named
test directories. Pair symbol references with scoped literal searches for dynamic
imports, string-named patches and command dispatch. A transport migration must
move its failure injection and prove the replacement was exercised; a mock on an
unused path is not evidence. Include return-value and parameterized tests across
package boundaries. Before full proof, account for each direct consumer and its
distinguishing case; an old assertion is changed only when accepted intent
supersedes it, while stronger sibling obligations remain tested. Record this
closure in normal test evidence, not a second dependency registry.

Retirement tests must distinguish a historical path mention from an executable
dependency. Exercise a real live consumer and its exit, native lock contention,
dependencies changing between effects, partial failure and fresh retry. Observe
activation and reclamation independently: a deferred cleanup neither erases a
successful activation nor justifies a success verdict for the whole repair.
Delete the old lifetime heuristic, not the historical evidence that exposed it.
One successful cleanup does not prove sustained or strong-kill boundedness.

Execute admission checks and their dependent write in one failure-propagating
control flow. Validate the JSON verdict, exact HEAD, target paths and preimage
before applying a patch; every subprocess must have checked success. A shell
assertion followed by an independent write is not a guard. Replay denied and
unknown decisions, stale preimages and successful admission against disposable
bytes before using an amended recipe. If an unauthorized write occurs, stop,
retain its exact diff, obtain rollback admission and verify the original bytes
before obtaining a new forward decision; later permission is not retroactive.

Move prevention to the earliest boundary that has enough information:

```text
declaration/schema -> effect admission -> native execution -> verification -> projection
```

Judge learning by a previously missed fault now rejected, a valid path restored,
less repeated work, or a retired duplicate, not by added prose or test count.
When a correction fails twice, revisit the owner and model before another patch.

For slow iteration, profile the complete loop and distinguish resource preparation,
observation, execution, proof, archive and publication. Count native calls and
transferred bytes alongside wall time; cumulative parallel durations do not add
up to wall time. Trace repeated work to its owning input and lifetime before
adding a cache, increasing concurrency or rebuilding unchanged supply. A cache
may reuse validated computation, never current authorization. Compare identical
valid and invalid workloads, plus cold/warm and drift behavior, before claiming
an improvement. Keep native notifications independent of unused CLI or admission
initialization. Shared immutable inputs do not imply shared mutable fixture state.

Check changed failure probes themselves: a damaged-byte test must prove that its
mutation actually changed the selected bytes before asserting rejection. Run the
new smallest case before expanding the affected matrix; a failure goes back to
that case, not another unconditional full-suite run. Read archived results only
for comparison, and retain one current attempt and its actual completion.

## Interrupted Execution

Observe the original process or tool handle before waiting, recovering or
restarting. A task marked active, an old running receipt or a lock filename does
not establish liveness. A polling timeout alone does not establish termination.
After confirmed termination without a complete result, keep the attempt
unproved, retain its bounded failure evidence, and reclaim only verified owned
scratch. Never merge incomplete coverage into a new proof or infer success from
the absence of an error report.

If observed execution exceeds the admitted envelope, interrupt only that exact
owned attempt, verify descendant exit and scratch cleanup, then rederive the
correct closure and controls. Do not label an intentionally interrupted attempt
a product regression or erase its evidence with the replacement run.

`tools/ci/python_test_gate.py` owns test-attempt isolation. Under its existing
coverage lock, it invalidates the previous completion marker before preparation
and writes a new marker only after tests, cleanup and source freshness succeed.
Single-attempt execution clears prior partial and sharded output. Cleanup must
not follow directory links or change permissions on external hard-linked files.
Normal cleanup is not proof of SIGKILL recovery or sustained storage boundedness;
those require real fault and retention tests at the responsible owner.
