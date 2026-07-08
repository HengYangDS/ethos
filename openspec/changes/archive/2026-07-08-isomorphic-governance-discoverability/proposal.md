## Why

ETHOS already uses one governed repository model and exposes that fact through
`governance_context`, profile contracts, and tests. The first-glance reader path
still made the idea harder to discover than it should be: a human or agent could
see the transition loop without immediately seeing that ETHOS governs itself and
adopted repositories through the same kernel.

This change promotes the existing isomorphic-governance contract into the first
reader surfaces without adding a new product form, command plane, or subsystem
name.

## What Changes

- Add an `Isomorphic Governance` first-glance section to `README.md`.
- Clarify the Product Design Contract so the `product` profile and adopter or
  domain profiles are described as profiles and adapters over the same kernel.
- Add a glossary entry so humans and agents can find the term directly.
- Add an architecture regression test that keeps the phrase and its boundaries
  discoverable in the first-glance docs.
- Add this OpenSpec carrier, claim, and chronicle evidence for the governance
  documentation change.

## Capabilities

- `repository-governance`: subject=isomorphic-governance-discoverability;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation;
  facet:surface=docs,openspec,evidence; facet:authority=docs,test,openspec,claim,evidence

## Out Of Scope

- No new command, profile kind, ontology role, or truth store.
- No adopter repository mutation.
- No claim that remote publication or hosted CI has completed.
- No line-by-line mapping from `问道` into feature names.
