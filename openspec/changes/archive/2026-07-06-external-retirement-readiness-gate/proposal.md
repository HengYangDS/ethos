# external-retirement-readiness-gate

## Why

External ETHOS can only replace an adopter's embedded ETHOS backend when the
retirement decision is executable and evidence-bound. Generic shadow parity can
prove command behavior, but it does not by itself prove that the adopter has
switched to an external default, frozen the embedded backend, preserved rollback,
or kept adopter-private profile roots out of product ontology.

## What Changes

- Add a generic fleet retirement-readiness gate for adopted repositories.
- Read the adopter `.ethos/profile.toml` instead of product-core adopter
  directories.
- Require `.ethos/profile.toml` as binding manifest and `.config/` as execution
  config root when declared by the adopter profile.
- Combine profile checks, product-boundary checks, parity gaps, and shadow
  parity into one retirement verdict.
- Report lifecycle gaps separately from parity/shadow gaps.

## Capabilities

- `ethos-repository`: subject=external-retirement-readiness-gate; reuse=extend; change=modify; facet:lifecycle=adoption,retirement,validation; facet:surface=cli,docs,openspec,test,evidence; facet:authority=source,test,docs,openspec,evidence

## Out of Scope

- No adopter-specific product directories are introduced.
- No reference-adopter embedded backend is deleted or frozen by this change.
- No rollback-window completion or final Retirement Decision is claimed.

## Impact

The product gains a reusable executable gate that can show when external ETHOS is
strong enough for retirement and when remaining blockers are true lifecycle
blockers rather than stale parity evidence.
