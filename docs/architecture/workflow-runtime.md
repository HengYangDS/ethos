---
subject: ethos:workflow-runtime
role: explanation
state: canonical
relations:
  canonical_for: workflow runtime read model
  informed_by: docs/research/workflow-runtime-frameworks-20260709.md
---

# Workflow Runtime

ETHOS owns a workflow runtime read model, not a private orchestration truth
store. The runtime borrows useful practice value from external systems while
preserving the ETHOS command plane and repository authority order.

## Root Model

The deeper model is not tool adoption, workflow enthusiasm, or a list of
parallel mechanisms. ETHOS treats work as the vessel for testing understanding:

```text
practice as vessel -> evidence as verification -> commitment as law -> retirement as non-attachment
```

The root object is therefore not a tool, not a workflow, and not even the
practice claim itself. The root object is a **governed commitment**: a bounded
promise about a repository subject that may become law only after authority,
evidence, claim, and chronicle binding.

Practice is the vessel. A **governed practice claim** is the evolution carrier
that asks whether a practice deserves to create, compose with, refine,
supersede, retire, or be rejected from those commitments:

```text
subject + question + claim + boundary + falsifiers
  -> candidate practices
  -> experiment and evaluation
  -> commitment targets
  -> commitment effect: create / compose / refine / replace / remove / reject
  -> fate: introduce / compose / refine / supersede / retire / reject
```

A framework, workflow, spec format, skill pack, task graph, or scenario system
is only a carrier of a practice. Candidate sets, experiments, evaluation
records, practice changes, runtime nodes, event streams, and handoff packages
are subordinate projections that help decide the commitment effect. This is why
ETHOS should not argue from Comet, OpenSpec, Spec Kit, Task Master, BMAD,
Superpowers, Agent OS, OpenSPDD, Shotgun, fspec, or any adjacent tool as an
ontology anchor. Each can carry a practice, none can become the center.

The practice claim may be introduced, composed, refined, superseded, retired, or
rejected according to its relation to existing commitments and the evidence it
can bind. Its deeper outcome is the commitment effect: create a new commitment,
compose with one, refine one, replace one, remove one, or refuse to admit one.
This is the operational reading of the root constraint: do not cling to the
vessel; use the vessel to verify the Dao of the work, then either canonize the
verified commitment or release the vessel.

Therefore ETHOS asks four questions before it adopts anything from Comet,
OpenSpec, Spec Kit, Task Master, BMAD, Superpowers, Agent OS, OpenSPDD, Shotgun,
fspec, or similar frameworks:

1. What practice is being tested, independent of the tool that carries it?
2. What evidence would falsify or confirm it?
3. What commitment would be created, preserved, refined, replaced, removed, or
   refused if judgment passes?
4. What should happen to the practice carrier once the commitment effect is
   known?

In this model, "upper replacement" is not the default move. If ETHOS does not
already own a practice in the same boundary, the correct act is introduction. If
the old practice is still valid but narrow, the act may be composition or
refinement. If the old practice is redundant, unsafe, or false, the act is
retirement. Supersession is reserved for the narrower case where a new practice
intentionally covers and replaces an incumbent commitment boundary with
migration, fallback, kill signal, evidence, and retirement conditions.

## Decision

The product decision is:

```text
OpenSpec = durable spec/change/archive carrier
Comet    = workflow-runtime practice reference
ETHOS    = governing kernel and command plane
```

ETHOS therefore absorbs selected runtime practices and rejects external
lifecycle authority:

| External practice carrier | ETHOS adoption |
| --- | --- |
| Comet transition table | Declare transitions in `system/workflows.toml`. |
| Comet guarded transitions | Map guards to ETHOS guard names and proof/admission gates. |
| Comet run state | Use machine-owned run snapshots under ignored/runtime or evidence boundaries only. |
| Comet state events | Treat raw event streams as generated state until curated into Chronicle evidence. |
| Comet handoff hash | Use digest-bound handoff packages over source refs and evidence refs. |
| Comet SkillBundle validation | Keep repo-local skills as digest-bound package projections. |
| Comet eval metrics | Allow optional skill eval metadata, subordinate to proof and claims. |
| OpenSpec archive/change carrier | Keep official OpenSpec as the mandatory spec carrier. |
| Task ledgers / boards | Keep as intake/projection adapters, not lifecycle truth. |

## Authority Model

The runtime reads lower surfaces and emits projections:

```text
Git facts
+ OpenSpec carrier state
+ system/workflows.toml
+ claims and evidence
+ local profile
= workflow runtime read model
```

It does not mint truth. Truth remains source, tests, schemas, governed docs,
OpenSpec records, claims, evidence, command JSON, and Chronicle records after
promotion.

## Evolution Layer Boundary

ETHOS also owns a learning and evolution mechanism. It is separate from the
workflow runtime:

```text
research / review / feedback
        -> hypothesis
        -> bounded experiment
        -> proof and evaluation
        -> decision / canonization
        -> retirement or archive
```

The canonical product expression is already present in `evolution/ledger.toml`,
`evolution/campaigns/`, `docs/research/`, OpenSpec changes, claims, evidence,
and chronicle records. The workflow runtime may project whether a hypothesis,
experiment, or campaign step has the required Work Lane, OpenSpec carrier,
guards, and evidence refs. It must not store hypotheses or experiments as hidden
runtime phases.

Therefore, a framework study such as the Comet/OpenSpec research is not merely a
workflow run. It is a research input that can produce a falsifiable hypothesis,
a bounded experiment, proof evidence, and then a decision to create, revise,
replace, retire, or refuse a commitment. The durable unit is the governed
commitment; the practice claim is the evolution carrier that helps execute and
inspect it.

## Practice Selection And Fate

ETHOS must support **multi-candidate selection**, but the more fundamental model
is not "always supersede." ETHOS governs the commitment effect of trustworthy
practice claims.

- A practice claim names the subject, question, boundary, claim, falsifiers,
  candidate set, experiment, evaluation, commitment targets, commitment effect,
  and fate records.
- A candidate set is a group of competing practices, frameworks, adapters,
  method packs, projections, or implementation strategies that answer the same
  governance question.
- Selection is evidence-weighted: proof results, eval metrics, review findings,
  blast radius, reversibility, maintenance cost, research support, projection
  boundary, and authority fit all contribute to the decision.
- If there is no incumbent practice in the same boundary, the correct fate is
  introduction, not supersession.
- If multiple carriers each contribute a bounded part, the correct fate is
  composition, not picking a monolith.
- If an incumbent remains valid but needs tightening, the correct fate is
  refinement.
- Supersession applies only when a new practice covers an existing commitment
  boundary and intentionally replaces it with migration, fallback, kill signal,
  evidence, and retirement conditions.
- If an incumbent commitment or candidate is redundant, unsafe, false, or no
  longer useful, the correct fate is retirement or rejection, not replacement
  theater.
- The winning practice is canonized through source/docs/schema/OpenSpec/claim/
  evidence/chronicle promotion. Losing or partial candidates are archived,
  rejected, composed, or retained as bounded learning, not silently forgotten.
- The evolution ledger records this as `practice_claim`, `candidate_set`,
  `experiment_protocol`, `evaluation_record`, and `practice_change` objects with
  explicit commitment effect so selection and fate can be audited as repository
  truth without making any one mechanism the center.

For the current framework-family study, Comet, OpenSpec-alone, Spec Kit-style
workflow grammar, Task Master-style task graph, fspec-style coverage mapping,
BMAD/Superpowers/Agent OS/OpenSPDD method packs, Shotgun-style UX, and related
systems are candidates at different layers. The selected upper practice is not a
single external framework. It is ETHOS-native trustworthy-practice evolution:
OpenSpec remains carrier, Comet-style runtime ideas are absorbed, task/scenario
ideas become projections, and method systems become replaceable practice packs.

## Runtime Contracts

### Workflow graph

`system/workflows.toml` declares:

- lifecycle states and initial state;
- transition edges;
- guards;
- required facts;
- invalid-state bindings;
- node kinds and enforcement modes;
- runtime-state and event locality;
- handoff package locality;
- eval metric names.

The graph is valid only when every transition references declared states and a
declared guard, and every invalid-state reference belongs to the ETHOS invalid
state taxonomy.

### Runtime state

Runtime state is machine-owned and can support recovery or diagnosis. It may be
stored under ignored `.ethos/` or build/runtime paths, or summarized into
evidence. Runtime state cannot by itself prove lifecycle completion, readiness,
landability, publication, or semantic truth.

### Events and Chronicle

Raw workflow events are generated runtime streams. They become trust-bearing
history only when a human or command closeout promotes the judged result into
`evidence/chronicle/` with bound evidence and claim refs.

### Handoff packages

A handoff package records:

- target actor or reviewer;
- intended use;
- source refs;
- source SHA-256 digests;
- proof/evidence refs;
- freshness state.

If source digests drift, the handoff is stale and cannot support a
trust-bearing claim until regenerated.

### Skill eval metadata

Skill eval metadata records optional evolution signals such as treatment id,
pass@k, weighted score, instability gap, failure refs, and evidence refs. It is
package metadata, not proof. Proof remains `ethos prove`, claims, evidence, and
promotion targets.

## Command Plane Projection

The runtime is exposed through existing command payloads:

- `ethos plan --json` includes `data.workflow_runtime` for planned transitions,
  guards, required facts, changed-path context, and linked evolution state.
- `ethos report --json` includes a workflow runtime scorecard layer and evolution bridge.
- `ethos prove`, `land`, and `publish` continue to be the trust-bearing
  lifecycle commands.

No second public workflow command is introduced.

## Rejected Authority Stores

These stores may be read as context or adapter inputs, but they are not ETHOS
lifecycle truth by default:

- `.comet.yaml`, `.comet/run-state.json`, `.comet/state-events.jsonl`;
- `.taskmaster` task JSON;
- `.specify` workflow state;
- vendor prompt folders;
- hosted CI UI state without bound evidence;
- assistant memory or session logs.

## Acceptance

The workflow runtime is acceptable when:

1. the workflow contract validates against schema and graph rules;
1. `plan` and `report` project runtime readiness without adding lifecycle
   commands;
1. handoff and run-state schemas are present;
1. skill eval metadata validates without replacing proof;
1. the evolution ledger validates candidate selection, experiment protocol,
   evaluation, and practice-change records for this adoption decision;
1. OpenSpec lifecycle validation, focused tests, and HEAD-bound proof pass.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Action Graph](action-graph.md),
[Local State](local-state.md), [OpenSpec Governance](../governance/openspec-governance.md),
and [Workflow Runtime Framework Research](../research/workflow-runtime-frameworks-20260709.md).
