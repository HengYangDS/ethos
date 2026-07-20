# Typed Semantic Attestation Receipts

## Why

Historical claims used `semantic` or `semantic_attested` labels without a
typed review receipt. A label alone cannot establish semantic review, yet
ordinary adopter workflows must remain portable and local-first.

## What Changes

- Demote existing unreceipted semantic labels to `digest_only` and remove
  semantic-review wording from their active claim summaries and bindings.
- Admit new `semantic_attested` claims only with a candidate-external typed
  receipt bound to claim, evidence digest, semantic scope, and exact HEAD.
- Remove the unused top-level claim scope mirror; promotion targets remain the
  single executable scope declaration.

## Capabilities

- `kernel`: subject=semantic-attestation-receipts; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=source,schema,test,openspec,evidence; facet:authority=source,test,schema,openspec,claim,evidence

## Out Of Scope

- A mandatory reviewer account, daemon, credential, network operation, or
  `yheng-agent-ethos` account.
- Cryptographic proof of semantic correctness or authority delegation.
