## Why

`evidence/` had become a mixed proof root: claim records lived under
`evidence/claims/`, parity evidence lived under `evidence/parity/`, but dated
human proof Markdown was loose at the evidence root or flat under
`evidence/chronicle/`. That weakened the terminal design's topic-scoped
evidence boundary and made the evidence tree harder to review.

## What Changes

- Keep the evidence root shallow: `README.md` plus semantic owner directories.
- Move judged Markdown proof records to `evidence/chronicle/<topic>/<date>.md`.
- Keep claim TOML in `evidence/claims/` and parity JSON in `evidence/parity/`.
- Update references and add architecture tests so loose dated evidence cannot
  re-enter the root or flat chronicle directory.

## Capabilities

- `repository-governance`: subject=evidence-topic-scoped-chronicle; reuse=extend; change=modify; facet:lifecycle=validation,archive; facet:surface=evidence,docs,openspec,test; facet:authority=evidence,claim,docs,openspec,test

## Out Of Scope

- No new evidence ontology or parallel proof store.
- No empty release, security, attestation, or manifest directories before real
  promoted records need them.
- No change to evidence file contents or claim digests beyond path references.
