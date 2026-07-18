## Why

ETHOS has a strong terminal governance target, but the productized OpenSpec
substrate still needs to be made explicit enough for adopters and future agents
to reproduce safely. The current workspace validates, yet it lacks in-repository
OpenSpec READMEs, family vocabulary, capability profile templates, and a fully
codified final-design carrier for the remaining productization decisions.

This change absorbs reusable mechanisms from `alternate mechanism corpus` and
`reference adopter workspace` without importing their domain vocabulary or creating a
second command plane.

## What Changes

- Add OpenSpec workspace guidance, change templates, capability templates, and
  family vocabulary.
- Extend capability profile contracts with decision axes and recommended facets
  so proposal routing is machine-auditable.
- Clarify the terminal product design around OpenSpec case carriers, Agent
  Invocation Envelope admission, topic-scoped evidence, and adopter scaffold
  acceptance.
- Keep official OpenSpec CLI semantics authoritative while ETHOS adds repo-local
  lifecycle, claim, evidence, and archive closeout checks.

## Capabilities

- `ethos-repository`: subject=terminal-final-design; reuse=extend; change=modify; facet:lifecycle=authoring,validation,archive; facet:surface=docs,openspec,scaffold; facet:authority=docs,openspec,claim,evidence
- `ethos-contracts`: subject=capability-profile-contract; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema,openspec; facet:authority=schema,openspec
- `ethos-adapters`: subject=openspec-lifecycle-review; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli; facet:authority=source,test,openspec

## Out Of Scope

- This change does not collapse the Python package topology.
- This change does not implement the full hook runtime or host pre-tool adapter.
- This change does not publish distributions or run remote hosted CI.
- This change does not make OpenSpec the public ETHOS command plane.
