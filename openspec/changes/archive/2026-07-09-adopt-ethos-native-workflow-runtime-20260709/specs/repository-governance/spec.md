## MODIFIED Requirements

### Requirement: Evolution Ledger Protocol
ETHOS SHALL keep reviewed evolution records and active hypotheses in one
repository-truth ledger at `evolution/ledger.toml`.

#### Scenario: workflow runtime bridges to evolution without owning it
- **WHEN** ETHOS projects workflow runtime readiness for a research, hypothesis, experiment, or campaign-driven change
- **THEN** the runtime projection references the evolution ledger or campaign manifest when present
- **AND** hypotheses, experiments, evaluations, canonization, and retirement remain governed by evolution records, OpenSpec carriers, claims, evidence, and Chronicle
- **AND** runtime state does not replace `ethos campaign hypotheses`, `ethos campaign status`, or `ethos quality evidence-freshness` as evolution governance surfaces


## ADDED Requirements

### Requirement: Practice Selection And Fate
ETHOS SHALL support governed practice claims, evidence-weighted selection among
competing hypotheses, designs, adapters, method packs, or implementation
strategies, and explicit practice fate decisions: introduce, compose, refine,
supersede, retire, or reject.

#### Scenario: practice claim carries commitment effect
- **WHEN** ETHOS evaluates a reusable practice or framework-family proposal
- **THEN** the ledger records a practice claim with subject, question, claim, boundary, falsifiers, incumbent relation, candidate set, experiment protocol, evaluation record, commitment effect, practice-change refs, commitment targets, evidence refs, and decision refs
- **AND** the practice claim remains an evolution carrier for effects on governed commitments rather than the root authority
- **AND** candidate sets, experiments, evaluations, practice-change records, runtime nodes, task graphs, and method packs remain subordinate projections of that claim

#### Scenario: candidate set is evaluated
- **WHEN** ETHOS compares multiple candidate practices for the same governance question
- **THEN** the candidates are represented as research, hypotheses, experiments, eval metadata, reviews, claims, evidence, or OpenSpec carriers
- **AND** the selected practice records why it wins over alternatives
- **AND** rejected candidates are archived, retired, or retained as bounded learning

#### Scenario: practice fate is classified
- **WHEN** ETHOS classifies a practice change
- **THEN** the practice-change record states whether it introduces, composes, refines, supersedes, retires, or rejects a practice, and records boundary, commitment effect, evidence, decision refs, and incumbent-specific migration or retirement fields when applicable
- **AND** the practice fate is recorded through evolution records, claim/evidence/chronicle rather than hidden runtime state


#### Scenario: ledger records candidate selection objects
- **WHEN** `evolution/ledger.toml` records a candidate selection decision
- **THEN** it includes a practice claim with commitment effect, a candidate set with at least two candidates, a bounded experiment protocol, an evaluation record with selected and rejected candidates, and a practice-change record that distinguishes introduction from real supersession and retirement
- **AND** every object binds evidence and decision refs instead of relying on assistant memory


### Requirement: Practice Evolution Kernel
ETHOS SHALL govern tools, frameworks, workflows, skills, task graphs, scenario
systems, and specs as practice carriers rather than as authorities.

#### Scenario: practice is judged before carrier adoption
- **WHEN** ETHOS evaluates an external framework or internal workflow proposal
- **THEN** the evaluation identifies the practice being tested, the evidence that would confirm or falsify it, the repository commitment effect it would create, compose, refine, replace, remove, or reject, and the correct fate after judgment
- **AND** the fate is one of introduce, compose, refine, supersede, retire, or reject according to its relation to incumbent boundaries
- **AND** no carrier becomes lifecycle truth without source, schema, OpenSpec, claim, evidence, and Chronicle promotion
