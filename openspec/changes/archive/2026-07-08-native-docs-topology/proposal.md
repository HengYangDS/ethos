---
subject: ethos:native-docs-topology
reuse: extend
change: modify
facet:lifecycle: governance
facet:surface: docs
facet:authority: repository-governance
---

# Native Documentation Topology

## Why

The prior documentation topology encoded lifecycle time in physical roots. That
made directory names compete with repository truth: a file under a time-labeled
root could look current or future regardless of HEAD, authority order, proof,
evidence, or decision state.

ETHOS needs the sharper model: documentation paths classify function and
authority; lifecycle state is proven by repository facts and evidence.

## What Changes

- Remove `current`/`future` roots from the required docs kernel.
- Reject `current` and `future` as documentation state values.
- Do not replace them with new mandatory contract or evolution pseudo-lanes.
- Keep the common kernel to navigation, decisions, evidence, history, and
  reference.
- Keep product or adopter extension roots optional and domain-bounded.
- Update adoption scaffold, docs topology contract, generated-artifact path
  policy, command-surface policy naming, tests, and navigation docs.

## Out Of Scope

- No new truth store.
- No second docs command plane.
- No rewrite of superseded decision history.
- No claim that directory topology alone proves semantic correctness.
