## Why

ETHOS already gives caches, evidence, artifacts, and Work Lane virtual
environments semantic homes, but ordinary owner scripts and the installed Git
hooks still resolve a root `.venv` or invoke bare `uv run`. In a multi-checkout,
multi-agent repository that leaves the most common execution paths outside the
runtime topology: each checkout can silently create a competing root environment,
and a normal developer command has different state semantics from a Work Lane.

The product needs one explicit runtime bootstrap contract: source-bound execution
state is owned by the checkout; content-addressed dependency downloads are owned
by the host or CI cache policy. This removes root-environment creation from normal
ETHOS execution without inventing a global authority, runtime registry, or
cross-checkout shared environment.

## What Changes

- Add one repository-owned Python runtime bootstrap that binds `uv` project
environments to `build/runtime/venv` in the current checkout and establishes
explicit cache policy for interactive, hook, local-CI, and hosted-CI contexts.
- Route all executable Python owner scripts and local Git hooks through that
bootstrap or an explicitly passed interpreter; remove root `.venv` fallback from
normal product execution paths.
- Extend generated-artifact topology policy and its entrypoint audit so active
`uv` and Python producer paths cannot silently default to root `.venv` or a
checkout-local opaque uv cache.
- Update the Work Lane bootstrap contract, local-state inspection, documentation,
and adoption scaffolds so the product explains the same lifecycle distinctions
at every entrypoint.
- Preserve a migration path: legacy root `.venv` directories remain ignored,
non-authoritative local residue until a user removes them; no automatic deletion
or foreign-worktree cleanup is introduced.

## Capabilities

### Modified Capabilities

- `repository-governance`: The existing Work Lane runner requirement expands to
  cover provider-neutral, checkout-bound Python runtime execution in normal
  repository owner scripts and hooks, with separate source-environment and
  dependency-cache semantics. Generated-artifact topology gains an
  executable-entrypoint invariant.

## Impact

- `tools/ci/scripts/`, `.githooks/`, and local/hosted CI projections.
- Generated-artifact policy, its packaged mirror, audit implementation, and
  local-state audit configuration.
- Work Lane CLI bootstrap payloads; repository and adopter documentation;
  adoption scaffold templates.
- Focused runtime, hook, topology, local-state, and scaffold tests; the full
  proof/closeout loop after implementation.
