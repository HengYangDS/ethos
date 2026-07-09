## Context

ETHOS already declares that repository state is derived, not stored in a private
state-machine database:

```text
OpenSpec change + Git facts + evidence manifests + system/workflows.toml + profile = derived state
```

The framework study sharpened what is missing. OpenSpec is strong as the durable
change/spec/archive carrier. Comet 0.4 is stronger as a workflow runtime and
skill/eval harness. Spec Kit, Task Master, BMAD, Superpowers, Agent OS,
OpenSPDD, Shotgun, fspec, and adjacent systems contribute other useful practice
patterns. The adoption target is therefore not a Comet import and not another
framework layer. It is an ETHOS-native runtime/evolution read model for the root
cycle: practice as vessel, evidence as verification, commitment as law, and
retirement as non-attachment.

The key abstraction is governed commitment, not mechanism. A practice
claim is the evolution carrier for a proposed commitment effect: it binds a
subject, question, claim, boundary, falsifiers, candidate set, experiment,
evaluation, commitment targets, commitment effect, and fate records. Workflow
runtime, candidate comparison, handoff freshness, skill eval metadata,
task/scenario projections, and method-pack invocation are subordinate surfaces
that help test or execute that claim.

## Design

The runtime is layered under the existing kernel:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

It adds these ETHOS-owned contracts:

1. `system/workflows.toml` remains the declared lifecycle graph. It may now name
   workflow nodes, node edges, enforcement mode, event streams, run-state
   locality, handoff package locality, and eval metrics.
2. `ethos_core.contracts.workflow` validates the declared workflow graph and
   exposes deterministic IR/read-model helpers.
3. `ethos.repository.workflow.runtime` combines workflow contracts with
   workspace status, claims, and OpenSpec shape into a read model.
4. `ethos plan --changed --json` includes workflow runtime planning data next to
   the deterministic action graph.
5. `ethos report --json` includes workflow runtime readiness as a scorecard
   layer.
6. Handoff packages are digest-bound source bundles. They can be generated or
   stored under ignored/runtime or evidence boundaries, but are not truth until
   promoted into evidence/chronicle.
7. Skill eval metadata is optional manifest metadata. It records expected metrics
   such as pass@k, instability gap, treatment, and evidence refs; it does not
   replace proof or skill package digest validation.
8. `evolution/ledger.toml` records `practice_claim` as the evolution carrier
   over `candidate_set`, `experiment_protocol`, `evaluation_record`, and
   `practice_change`, with explicit `commitment_effect`, so introduction,
   composition, refinement, supersession, retirement, and rejection are judged
   as effects on governed commitments rather than unrelated mechanism labels.


## Evolution Relationship

ETHOS already has a learning/evolution path:

```text
observe -> hypothesize -> experiment -> prove -> canonize -> retire
```

That path is higher-level than the workflow runtime. Research and investigations
live in `docs/research/` and may inform OpenSpec changes. Falsifiable
hypotheses live in `evolution/ledger.toml`. Long-running coordinated work lives
in `evolution/campaigns/<campaign-id>/campaign.toml`. Experiments are bounded
changes or evidence packages that test hypotheses through normal Work Lane and
proof mechanics. The workflow runtime only projects execution readiness and
guard state for these objects; it does not own the learning lifecycle.

In this change, the ledger's practice claim records that ETHOS is introducing a
new upper practice-evolution boundary, not superseding OpenSpec. OpenSpec
continues as the spec/change/archive carrier. Comet and adjacent systems were
research references and practice carriers, not incumbents inside ETHOS
authority. Supersession remains available only when a new practice covers an
existing incumbent boundary and carries migration, fallback, kill signal,
evidence, and retirement conditions.

## Boundary Rules

- The public lifecycle remains `status -> plan -> prove -> land -> publish`.
- OpenSpec remains the mandatory change/spec/archive carrier.
- Backlog/intake stays projection/UI/intake.
- Work Lanes own isolated mutation and replay.
- Claims bind evidence; they do not own lifecycle state.
- Chronicle records judged history; raw runtime events are generated state until
  promoted.
- Method packs remain replaceable adapters.
- Research, hypothesis, experiment, evaluation, canonization, and retirement remain evolution/campaign concerns, not runtime phase names.

## Alternatives

- **Adopt Comet directly.** Rejected because `.comet.yaml`, `.comet/run-state`,
  and Comet phase names would create a second lifecycle store and command-plane
  center.
- **Use OpenSpec alone.** Rejected because OpenSpec validates spec/change/archive
  carriers but does not cover resumable execution state, handoff freshness,
  skill bundle/eval control, or guarded runtime events.
- **Adopt a task-ledger system.** Rejected for this change because Task Master
  and similar systems conflict with ETHOS Backlog/intake and Work Lane ownership
  if promoted as truth.

## Proof Strategy

- Validate `system/workflows.toml` against its schema and workflow graph checks.
- Run focused unit tests for workflow contract validation, plan projection,
  report projection, and skill eval metadata validation.
- Run OpenSpec lifecycle validation for this change.
- Run HEAD-bound executed proof before land.
- Record claim and chronicle evidence before closeout.


## Practice Selection And Fate

This change treats Comet, OpenSpec-alone, and adjacent SDD/agent workflow
systems as carriers or candidate practices under one governed commitment model;
the practice claim is the evolution carrier, not the root authority. ETHOS
selects practices by evidence-weighted fit and supports practice fate
governance: a practice may create, compose with, refine, replace, remove, or be
rejected from governed commitments according to its relation to incumbent
boundaries and evidence.
