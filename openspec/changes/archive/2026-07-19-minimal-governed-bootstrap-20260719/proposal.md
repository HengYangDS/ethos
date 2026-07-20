## Why

`ethos adopt` currently turns a new repository into a 66-file, roughly
1,400-line copy of ETHOS documentation, decisions, OpenSpec families, skills,
ignored-state placeholders, and provider projections. Template rendering made
that copy deterministic, but did not make it minimal: the generated skeleton is
larger than the binding facts needed to recognize and govern an adopter.

## What Changes

- **BREAKING** replace the complete governance skeleton with the smallest
  truthful bootstrap required by current runtime behavior.
- Keep one `.ethos/profile.toml` binding manifest and create other carriers only
  through the capability that owns them.
- Stop creating `.gitkeep`, decision/doc trees, capability families, skill
  packages, release policy, generated-artifact policy, or provider CI by
  default.
- Remove scaffold declarations, templates, digest snapshots, profile selection,
  overlay, `init`, complete-skeleton assertions, and compatibility behavior that
  exist only for the retired output set.
- Keep default read-only planning, strict conflict reporting, and explicit apply
  semantics over the one-file output set.
- Keep absent optional capabilities inert until explicitly selected or activated
  by a matching material change; retain native correctness and material-scope
  fail-closed behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=minimal-adopter-binding; reuse=extend;
  change=modify; facet:lifecycle=adoption; facet:surface=cli,contract;
  facet:authority=source,test,openspec. Adoption SHALL create only the binding
  carrier required to recognize an adopter; optional governance surfaces SHALL
  be created by the capability that owns them, not preallocated by bootstrap.

## Impact

- Adoption planner, repository profile contract, and CLI surface.
- Adopter binding, governance-kernel, CLI and contract tests.
- Generated docs/OpenSpec/skill/provider templates, their manifest, and Jinja2.
- Active docs, rules, campaign declarations, format policy, source-budget
  contracts, and claims that still name the retired paths.
- Existing adopters are not migrated or updated; no compatibility chain is retained.

## Out Of Scope

- No Copier, Cookiecutter, Projen, project-update engine, answers file, migration
  ledger, generated business Python, or editable generated truth.
- No weakening of Work Lane, proof, OpenSpec, evidence, or hosted-provider trust
  boundaries.
