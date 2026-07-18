# Isomorphic Governance Context Envelope

## Problem

ETHOS already defines one governed repository model for product and adopted
repositories, but some primary command JSON results expose that model only inside
nested audit payloads or not at all. Consumers then have to infer command
semantics from command-specific data shapes, which weakens the product promise
that profiles and adapters sit over one kernel rather than creating a second
truth center.

## Change

Expose `governance_context` as a top-level result envelope on the primary command
plane: `status`, `plan`, `prove`, `land`, `publish`, `orient`, and `report`.
Keep command-specific `data` payloads pure: for example, `status.data` remains a
workspace-status object that validates against `workspace-status.schema.json`.

## Capabilities

- `repository-governance`: subject=isomorphic-governance-context-envelope; reuse=extend; change=modify; facet:lifecycle=runtime,validation,archive; facet:surface=cli,schema,docs,openspec,evidence,test; facet:authority=source,test,schema,docs,openspec,claim,evidence

## Out Of Scope

- No new command, truth store, repository subject kind, or provider ontology.
- No change to transition command semantics or mutation authority.
- No pollution of native command `data` contracts such as workspace status.
- No hosted CI, remote publication, or adapter-specific success claim.
