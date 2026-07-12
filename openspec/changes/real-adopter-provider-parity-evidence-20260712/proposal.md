## Why

ETHOS has a current-HEAD local exercise against an isolated real-adopter clone.
Its result needs a reviewable record without tracking the adopter, temporary
paths, provider state, credentials, or raw proof bundle.

## What Changes

- Add a digest-bound claim and Chronicle for `generic`, `github`, and `gitlab`.
- Bind product/adopter revisions, profile outcomes, preservation assertion, and
  SHA-256 of the host-local bundle.
- Activate the required evidence and history documentation entrypoints as
  routes to existing claims, Chronicles, parity records, decisions, and the
  OpenSpec archive; do not duplicate proof payloads.
- Keep the evidence local-only and non-authorizing.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=external-adopter-provider-parity-evidence; reuse=extend; change=modify; facet:lifecycle=evidence,claim; facet:surface=adoption,parity,chronicle,docs; facet:authority=source,claim,evidence,openspec.
- `quality`: subject=source-budget-evidence-carrier; reuse=extend; change=modify; facet:lifecycle=admission,archive; facet:surface=source-budget,format; facet:authority=policy,claim,openspec.

## Out Of Scope

- Changing the adoption planner, provider adapters, or runtime.
- Requiring `yheng-agent-ethos`, an account, credential, key, daemon, or network service.
- Claiming semantic compatibility, hosted CI, remote publication, provider authority, independent review, or semantic correctness.

## Impact

- Carrier, claim, Chronicle, and bounded policy record only; no runtime, planner, adapter, adopter, remote, or account change.
