## Why

Research into Comet 0.4, OpenSpec, Spec Kit, BMAD, Superpowers, Task Master,
Agent OS, OpenSPDD, Shotgun, and fspec showed that the earlier "Comet vs
OpenSpec" frame is a layer error. OpenSpec remains the right durable
specification/change/archive carrier, while Comet exposes missing workflow
runtime practices: explicit transition tables, guard semantics, resumable run
state, append-only events, handoff hashing, skill bundle validation, and eval
metadata.

ETHOS needs the useful practices without admitting `.comet` state, task
ledgers, or external workflow commands as lifecycle truth. It also needs to keep
research, hypotheses, experiments, evaluations, and canonization in the existing
evolution/campaign layer rather than hiding them inside a runtime state machine.
This change promotes the research outcome into repository truth and adds a
minimal ETHOS-native workflow runtime read model under the existing kernel and
command plane.

The deeper design target is governed commitment. ETHOS should decide
whether a practice deserves to create, compose with, refine, replace, remove, or
be rejected from a repository commitment by binding its subject, boundary,
falsifiers, candidate comparison, experiment, evaluation, commitment targets,
commitment effect, and fate. The runtime and framework mechanisms are
projections that help execute that claim; they are not the root object.

## What Changes

- Record the framework research as a governed research document.
- Add a workflow-runtime architecture document that keeps lifecycle truth
  derived from Git, OpenSpec, claims, evidence, and `system/workflows.toml`.
- Extend workflow contracts with node, edge, enforcement, event, runtime-state,
  handoff, and eval metadata fields inspired by Comet but named in ETHOS terms.
- Add schemas for machine-owned workflow run snapshots and digest-bound handoff
  packages.
- Add a minimal runtime read model surfaced through existing `plan` and `report`
  payloads; no new public lifecycle command is introduced.
- Bridge the runtime read model to existing evolution hypotheses and campaigns so
  research and experiments remain governed learning objects.
- Add `practice_claim` as the upper practice-evolution ledger record over
  candidate sets, experiments, evaluations, and practice-change fate.
- Extend skill package validation with optional eval metadata so repo-local
  skills can record pass@k and instability-gap evidence without becoming truth
  stores.

## Capabilities

- `kernel`: subject=workflow-runtime; reuse=extend; change=modify; facet:lifecycle=runtime; facet:surface=schema; facet:authority=schema
- `contracts`: subject=workflow-runtime-contract; reuse=extend; change=add; facet:lifecycle=runtime; facet:surface=schema; facet:authority=schema
- `command-plane`: subject=workflow-runtime-projection; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli; facet:authority=source
- `adapters`: subject=workflow-runtime-adapters; reuse=extend; change=modify; facet:lifecycle=runtime; facet:surface=docs; facet:authority=docs
- `assistant-projections`: subject=skill-eval-metadata; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=skill; facet:authority=schema
- `repository-governance`: subject=evolution-runtime-bridge; reuse=extend; change=modify; facet:lifecycle=runtime; facet:surface=docs,cli; facet:authority=docs,source

## Out Of Scope

- Adopting Comet as a dependency, command plane, or `.comet` truth store.
- Replacing OpenSpec, Backlog/intake, Work Lane, Claim, Evidence, or Chronicle
  ownership.
- Adding a long-lived orchestration service, private state-machine database, or
  second lifecycle command set.
- Adopting Task Master, Spec Kit, BMAD, Superpowers, Agent OS, OpenSPDD,
  Shotgun, or fspec wholesale.


## Practice Selection And Fate

This change treats Comet, OpenSpec-alone, and adjacent SDD/agent workflow
systems as carriers or candidate practices under one governed commitment model;
the practice claim is the evolution carrier, not the root authority. ETHOS
selects practices by evidence-weighted fit and supports practice fate
governance: introduce when no incumbent commitment owns the boundary, compose
when bounded carriers each contribute, refine when an incumbent remains valid,
supersede only when a new practice covers and replaces an incumbent commitment
boundary, retire when an incumbent is redundant or wrong, and reject when a
candidate remains bounded learning.
