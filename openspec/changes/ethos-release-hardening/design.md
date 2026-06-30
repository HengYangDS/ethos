## Context

ETHOS is now its own product repository. It must use official OpenSpec records
for self-governance while keeping `ethos ...` as the single public command
plane. Existing package-root `__init__.py` files also acted as forwarding
surfaces, which conflicts with the product rule against re-export shells.

Git commit verification has two layers: local Git cryptographic verification
and GitLab service-side verification. ETHOS must model both separately because
GitLab can mark a locally valid SSH-signed commit as unverified when the
signing key or email is not registered on the GitLab account.

## Goals / Non-Goals

**Goals:**

- Keep OpenSpec as an official self-governance capability.
- Remove package-root re-export wrappers.
- Add release policy, SBOM, attestation, and history identity checks.
- Expose agentic context as a thin MCP/ACP projection over repository truth.

**Non-Goals:**

- Do not make OpenSpec a second public command plane.
- Do not claim GitLab service-side verification from local Git output alone.
- Do not move product behavior into `tools/` or host-local agent state.

## Decisions

- Import from semantic modules directly instead of package roots. This makes
  ownership explicit and prevents catch-all `__init__.py` surfaces.
- Keep `openspec/` tracked and official for ETHOS self-governance, but classify
  it as planning/governance records that feed source, docs, tests, and schemas.
  ETHOS calls the official OpenSpec CLI for health and strict validation instead
  of reimplementing OpenSpec parsing.
- Add `ethos quality history-identity` for raw Git metadata and signature audit.
  GitLab verification remains a separate service-side fact.
- Add release projections as deterministic JSON payloads before integrating
  external signing or SBOM tooling.

## Risks / Trade-offs

- GitLab verification may remain unverified without account-level signing key
  registration. Mitigation: report it as a release blocker instead of masking
  it.
- Removing root re-exports changes import ergonomics. Mitigation: tests enforce
  direct semantic imports.
- OpenSpec records can drift. Mitigation: run official OpenSpec validation in
  self-audit, architecture tests, and hosted CI while keeping ETHOS
  kernel/docs/tests as promotion targets.
