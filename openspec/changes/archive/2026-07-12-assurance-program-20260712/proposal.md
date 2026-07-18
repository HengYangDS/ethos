# Optional Independent Re-execution Assurance

## Problem

ETHOS correctly labels local proof as readiness, but adopters that elect a
separate re-execution boundary need an exact, provider-neutral receipt contract
without converting one workstation identity into product authority or burdening
every adopter.

## Change

Add action-scoped independent-verification admission for `publish`, protected
provider-local receipt verification, a one-shot independent-identity reference
adapter, and external-adopter policy fixtures and guidance.

## Capabilities

- `repository-governance`: subject=optional-independent-reexecution; reuse=extend; change=modify; facet:lifecycle=evidence,admission; facet:surface=publish,profile,adapter; facet:authority=source,test,docs,openspec

## Out Of Scope

- No mandatory verifier, account, daemon, scheduler, network dependency, or
  hosted status claim.
- No semantic-correctness claim from a receipt.
- No external-parity claim from generic product self-shadow.
