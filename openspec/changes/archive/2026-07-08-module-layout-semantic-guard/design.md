# Design

## Boundary

This change tightens the existing module-layout quality gate. It does not create
a new layout authority. The rule remains `rules/module_layout.md`; executable
ownership remains `.config/ci/scripts/run-module-layout.sh`; policy remains
`.config/checks/module-layout/policy.toml`; implementation remains under
`ethos.repository.policy.layout`.

## Mechanism

- `flat_growth_findings()` now treats a newly-created directory as governed
  growth when it receives more than `flat_growth_added_module_limit` direct
  modules in one change.
- `dynamic_compat_facade_findings()` reports ordinary modules that define a
  module-level `__getattr__`, because that is a lazy compatibility facade rather
  than a concrete semantic module.
- `module_layout_report()` includes the new findings in its required gaps and
  summary, so `ethos quality module-layout --json`, report, proof, local CI,
  hosted CI, and pre-commit all share the same verdict path.

## Trade-offs

A new semantic subpackage may still contain one or two direct modules before it
has enough internal structure to split further. More than two direct modules at
birth must already choose a semantic interior. This keeps the gate small and
avoids banning legitimate small packages while stopping one-shot flat buckets.
