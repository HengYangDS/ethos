## Why

The protected control-replacement verifier required a top-level `head` field
that native `ethos prove --execute --json` results do not emit. A real local
closeout therefore needed a handwritten compatibility envelope despite already
having a complete, HEAD-bound candidate proof. That indirection weakens the
meaning of "candidate proof" and is a generic bootstrap defect, not an adopter
or provider concern.

## What Changes

- Bind the external control-replacement verifier directly to the native
  executed-proof JSON contract.
- Require the command identity, executed state, result verdict, evidence HEAD,
  and provenance-predicate HEAD to agree on the candidate being promoted.
- Reject a bare `{head, state}` record rather than preserving it as a legacy
  compatibility format.
- Record the repair with an adapters OpenSpec delta, a bounded claim, and a
  Chronicle entry.

## Capabilities

- `adapters`: subject=control-replacement-bootstrap; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,docs,openspec,evidence,test; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Adding an adopter profile, provider adapter, agent account, credential,
  network service, daemon, or scheduler requirement.
- Changing branch-role semantics, the proof lattice, or the optional/default-off
  independent-verification extension policy.
- Modifying, landing, retiring, or cleaning any foreign Work Lane.
