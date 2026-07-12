## Why

ETHOS now has a current-HEAD local exercise against an isolated clone of a
real adopter.  Its durable conclusion must be reviewable without tracking the
adopter, local temporary paths, provider state, credentials, or a raw proof
bundle.  A small digest-bound record is therefore needed to preserve exactly
what the exercise observed and, equally, what it did not establish.

## What Changes

- Add a digest-bound claim and topic-scoped Chronicle for the current-HEAD
  overlay exercise across the `generic`, `github`, and `gitlab` profiles.
- Bind the product revision, isolated-adopter revision, profile outcomes,
  protected-surface byte-preservation assertion, and SHA-256 of the host-local
  raw bundle.
- Keep the evidence local-only: it neither changes adopter configuration nor
  claims remote publication, hosted execution, provider authority, semantic
  correctness, or an account requirement.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=external-adopter-provider-parity-evidence;
  reuse=extend; change=modify; facet:lifecycle=evidence,claim;
  facet:surface=adoption,parity,chronicle;
  facet:authority=source,claim,evidence,openspec.

## Out Of Scope

- Changing the adoption planner, provider adapters, or product runtime.
- Requiring `yheng-agent-ethos`, an account, credential, key, daemon, or
  network service.
- Claiming an adopter's semantic compatibility, hosted CI, remote publication,
  provider authority, independent review, or semantic correctness.

## Impact

- OpenSpec carrier, claim manifest, and Chronicle only.
- No product runtime, adoption planner, provider adapter, external repository,
  remote branch, credential, service, or local-account prerequisite changes.
