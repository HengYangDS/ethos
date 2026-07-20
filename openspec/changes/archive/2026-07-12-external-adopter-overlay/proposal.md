## Why

`ethos adopt` safely refuses to overwrite an existing repository's governance
surfaces. An isolated external-adopter pilot correctly exposed that the current
scaffold has no explicit way to preserve an adopter's existing
AGENTS entrypoint, OpenSpec workspace, documentation, and GitLab projection
while adding only ETHOS-owned binding surfaces. A fresh-repository scaffold is
therefore not sufficient evidence of practical external adoption.

## What Changes

- Add an explicit non-destructive overlay mode to `ethos adopt`.
- Keep strict adoption as the default: differing existing content remains a
  blocking conflict unless overlay mode is requested.
- In overlay mode, preserve declared adopter-owned entrypoints, documentation,
  OpenSpec, and hosted-provider projection files; create only missing
  ETHOS-owned binding, local-state, skill, evidence, and generated-artifact
  surfaces.
- Report preserved paths and their content digests as part of the adoption plan
  so an apply is reviewable and deterministic.
- Prove the behavior against an isolated clone of an external Git repository
  without mutating its source checkout or remote.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: adoption must support an explicit,
  non-destructive overlay for existing repository governance surfaces.

## Impact

- `ethos adopt` planner and CLI contract.
- Adoption unit and CLI-contract tests.
- Adoption architecture and fleet documentation.
- A bounded, local-only evidence exercise against an isolated external-adopter
  clone. No remote publication, provider account, key, daemon, or change to
  its source checkout is in scope.
