# Authoritative Adopter Material Scope Binding

## Why

ETHOS now evaluates the official OpenSpec lifecycle for both product and adopter
repositories, but an active Change alone does not establish that a material
adopter edit belongs to that Change. The missing product mechanism must bind
profile-declared material paths to an active Change without making OpenSpec
schema, proof gates, or a method package carry repository governance.

## What Changes

- Define a typed ETHOS-owned profile declaration for material path patterns and
  a strict Change-local `scope.toml` companion.
- Reuse one lifecycle read model for `lane prewrite`, `plan --changed`, and
  `prove`, sourced from the official OpenSpec active Change selection.
- Fail closed for absent, empty, invalid, or uncovered material declarations,
  while keeping unrelated invalid companions diagnostic rather than global
  blockers.
- Permit only the official new Change's own absent `scope.toml` bootstrap write.
- Update scaffold and canonical docs; add admission, planning, proof, contract,
  and bootstrap regressions.
- Bind the additive implementation to a named source-budget debt record and a
  follow-on compression wave without resetting the global baseline.
- Refresh the product's tracked generic shadow-parity witness after the
  parity-relevant implementation changes, before the committed-HEAD proof.

## Capabilities

- `repository-governance`: subject=adopter-material-change-scope-binding;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation;
  facet:surface=cli,profile,openspec,test,docs,scaffold;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Extending or replacing the official OpenSpec workflow schema or lifecycle.
- Putting lifecycle scope into `[proof] code_correctness_gates`, creating
  repository-specific private admission schemas, or promoting Superpowers (or
  any method pack) to governance authority.
- Retrospectively certifying historical adopter work or landing DDWG from an
  audit worktree.
