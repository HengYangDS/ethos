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

## Tightening Rule

Tightening means moving a late failure upstream in this order:

```text
incident -> diagnosis -> config owner -> script owner -> hook/CI projection -> proof gate -> schema/default
```

Do not add a hosted CI command when a local owner script or ETHOS command can own
that behavior. Do not add a new gate if an existing gate can expose the same
concern with clearer evidence.
