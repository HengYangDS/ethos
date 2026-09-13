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
   Nox exposes native checks; local CI selects the declared full closure, not a
   private session list. `tools/ci/scripts/` retains necessary platform adapters.
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
- Local CI retains the exact command/policy, source overlay, individual results,
  stdout/stderr and a failure receipt. It never claims hosted success or repository
  proof from that fallback receipt. Use exact committed full proof for acceptance.
- Hosted observation is a separately requested read after publication, never a
  dry-run success or a self-wait inside the pipeline being observed.

## Root Configuration Boundary

Root configuration is allowed only when the tool or substrate requires root-native
discovery and no explicit owner path can preserve the same behavior. `pyproject.toml`
stays package/workspace metadata. Ruff and pytest are owned explicitly by
`ruff.toml` and `.config/checks/pytest/pytest.ini`; owner
scripts pass those paths. Root `ruff.toml` is intentional; a second pytest or
Ruff configuration would be a competing owner.

## Learning And Failure Placement

For a reproduced failure, distinguish the observation from its causal hypothesis
and identify the violated invariant. Exercise the smallest real counterexample,
repair its existing semantic owner, remove the replaced path, and replay both
valid and invalid consumers. Use the existing Change for scope and acceptance,
the canonical plan for unresolved work, and exact receipts for results. Add a
Decision Record only for irreducible cross-Change rationale; do not add a feedback
ledger, lesson catalog, alternate rule registry or a copied adopter gate.

Move prevention to the earliest boundary that has enough information:

```text
declaration/schema -> effect admission -> native execution -> verification -> projection
```

Judge learning by a previously missed fault now rejected, a valid path restored,
less repeated work, or a retired duplicate, not by added prose or test count.
When a correction fails twice, revisit the owner and model before another patch.

## Interrupted Execution

Observe the original process or tool handle before waiting, recovering or
restarting. A task marked active, an old running receipt or a lock filename does
not establish liveness. A polling timeout alone does not establish termination.
After confirmed termination without a complete result, keep the attempt
unproved, retain its bounded failure evidence, and reclaim only verified owned
scratch. Never merge incomplete coverage into a new proof or infer success from
the absence of an error report.

`tools/ci/python_test_gate.py` owns test-attempt isolation. Under its existing
coverage lock, it invalidates the previous completion marker before preparation
and writes a new marker only after tests, cleanup and source freshness succeed.
Single-attempt execution clears prior partial and sharded output. Cleanup must
not follow directory links or change permissions on external hard-linked files.
Normal cleanup is not proof of SIGKILL recovery or sustained storage boundedness;
those require real fault and retention tests at the responsible owner.
