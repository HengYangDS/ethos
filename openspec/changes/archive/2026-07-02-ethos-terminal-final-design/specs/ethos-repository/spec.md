## ADDED Requirements

### Requirement: Productized OpenSpec Substrate

ETHOS SHALL provide an inspectable OpenSpec workspace substrate for product and
adopter repositories instead of treating an empty `openspec/` directory as
complete governance.

#### Scenario: OpenSpec substrate is inspectable

- **WHEN** ETHOS scaffolds or audits an OpenSpec workspace
- **THEN** the workspace includes guidance for the workspace, specs, and changes
- **AND** it includes family vocabulary and capability profile templates
- **AND** active changes remain case carriers rather than promoted truth.

### Requirement: Agent Invocation Admission Boundary

ETHOS SHALL describe mutation-capable agent invocation as an explicit admission
envelope over owner, target root, editor root, target paths, evidence class, and
promotion route.

#### Scenario: Invocation boundary preserves repository proof

- **WHEN** host readiness or assistant context is available
- **THEN** ETHOS may compose it as optional host evidence
- **AND** repository mutation and closeout still require Work Lane admission,
  claim binding, OpenSpec carrier readiness, and repository proof evidence.

### Requirement: Topic-scoped Evidence Closeout

ETHOS SHALL prefer topic-scoped closeout evidence bundles for long-running proof
so transcripts remain reviewable and do not become unstructured truth.

#### Scenario: Closeout evidence is reviewable

- **WHEN** a closeout proof package is summarized
- **THEN** evidence records identify topic, lane, proof class, commands, return
  codes, retained artifacts, HEAD binding, and proof boundaries.
