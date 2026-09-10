## Why

The declared proof graph and local CI independently select and schedule quality
checks. They can both pass while proving different obligations: local CI runs
security and delivery checks absent from full proof, while its private session
lists omit declared typing and budget gates. Existing dependency waves also run
a downstream effect after its prerequisite fails.

## What Changes

- Make local CI consume the existing declared gate graph and shared executor;
  remove its private check membership, scheduling and duplicate invocations.
- Register existing unrepresented quality owners with explicit network, write
  and evidence boundaries; retain offline correctness and distinguish external
  freshness and hosted observation from repository proof.
- Block dependent checks when a prerequisite fails or is unknown, retaining the
  exact failed edge and unexecuted result rather than running delivery anyway.
- Preserve the complete quality-system assessment and phased remediation in the
  existing terminal plan, including tools previously researched, unresolved
  scope gaps, native-rule tightening and resource costs.

## Capabilities

### Modified Capabilities

- `quality`: one dependency-aware execution graph determines quality coverage
  across local CI and repository proof, with truthful evidence-plane selection.

## Impact

`system/gates.toml`, the existing gate contract/compiler/runner, local CI and
its native Nox transports, their tests, quality documentation and authoritative
skills, and `docs/plans/terminal-governance-product-design.md`.
No new lane, tool catalog, quality platform or adopter-specific policy is added.
Ruff policy replacement, typing-scope repair, metric correctness, resource
recovery and structural simplification remain required subsequent owner-level
changes rather than unrelated implementations inside this Change.
