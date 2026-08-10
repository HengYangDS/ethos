# Declared publication peers

## Why

Publication currently assumes exactly one GitLab and one GitHub remote. A
repository with only an explicitly declared GitLab peer is therefore invalid,
even when its local verification and installation contracts are complete. The
same fixed-provider assumption leaks into publish observation, admission, and
reconciliation. Separately, hook installation leaves the obsolete
common-directory `ethos-runtime-python` locator behind although current hooks
and runtime manifests no longer consume it.

## What changes

- Replace fixed provider scalars with a zero-or-more collection of publication
  peers, each carrying a stable ID, provider, role, Git remote, and declared
  capabilities. Local-only, local plus either single provider, and local plus
  both providers are equally valid topologies.
- Validate uniqueness of peer IDs, providers, and remotes; reject ambiguous
  coexistence with retired scalar declarations.
- Observe, admit, reconcile, and publish only the declared peers. A CI surface
  is required only when the peer declares the `ci_cd` capability.
- Retire `ethos-runtime-python` only after package-only hook installation has
  validated the final runtime manifest and launchers.

## Out of scope

- Inventing a remote, hosted CI surface, or provider for an adopter.
- Changing an adopter's release policy, verification command, or installation
  command.
- The separate gate-owner topology and output-compaction product changes.

## Affected capabilities

- `repository-governance`: declared remote authority and admission.
- `distribution`: package-only publication and hook-runtime cleanup.
