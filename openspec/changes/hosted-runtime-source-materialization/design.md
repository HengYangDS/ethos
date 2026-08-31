## Context

The preceding Hosted run established two failures after its local archive and
proof had passed. Windows package-only installation failed because delivery and
runtime materialization independently reconstructed the `nodejs-wheel` layout;
one used the correct package-root `node.exe`, while the other used a nonexistent
`bin/node.exe`. GitHub repository proof and GitLab verification failed because a
proposal checkout first installed hooks and attempted to materialize an
accepted-source runtime, mixing mutation readiness into source proof.

## Goals / Non-Goals

**Goals:**

- Give installed Node path knowledge one product owner and migrate every
  consumer to it.
- Keep source proof read-only with respect to Git-common runtime and hook state.
- Preserve local status visibility and local mutation admission for selected
  immutable runtimes.

**Non-Goals:**

- No PATH fallback, platform retry, hard-coded alternate path, synthetic
  accepted ref, or provider-specific proof implementation.
- No change to package cache ownership, temporary-resource scavenging, or the
  broader runtime activation transaction; those retain their own bounded
  successor obligations.

## Decisions

Extend the existing runtime input-resolution module to own the platform-specific
Node executable and npm CLI coordinates. Runtime materialization, OpenSpec, and
delivery consume that owner directly. Delete the CI-only Node module and move
its tests to the product owner's test module. This is preferable to a new
toolchain package or Windows fallback because it removes two competing sources
of path truth.

Remove hook installation from both Hosted repository-proof projections. Keep
the existing Git identity/signing setup because tests exercise commit policy,
but stop describing it as write-admission activation. Source proof continues to
run through the checked-out lock and environment.

Remove local hook/runtime currentness from repository source audit. The public
status projection continues to report `hook_runtime` independently, while
mutation commands continue to enforce their own runtime and hook boundaries.
This separates source correctness from host-local activation instead of adding
a Hosted mode flag or weakening local write admission.

## Risks / Trade-offs

- **A consumer may still reconstruct a Node path later** → focused source scans
  and architecture tests require imports from the single resolver and reject
  the retired helper.
- **Removing hook activation could conceal a source mutation in CI** → Hosted
  proof remains read-only, while local mutation behavior is exercised by the
  existing lifecycle and package-only conformance tests.
- **Repository audit no longer proves local hook installation** → status and
  mutation admission remain the explicit owners of that host-local fact; full
  proof continues to test runtime installation as product behavior.

## Migration Plan

1. Add failing product-resolver and Hosted projection regressions.
2. Move all Node/npm consumers to the runtime input resolver and delete the
   CI-only helper and its standalone tests.
3. Remove Hosted hook activation and repository-audit coupling to local hook
   state, then regenerate provider projections.
4. Run focused tests, projection drift checks, exact-HEAD proof, archive and
   reproof, then observe both Hosted providers before accepted closeout.
