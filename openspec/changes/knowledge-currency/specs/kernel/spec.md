## MODIFIED Requirements

### Requirement: Minimal Semantic Kernel

ETHOS SHALL persist Attestation as its only durable semantic root and SHALL compile Commitment transiently from one exact official OpenSpec Change, without persisting it. Facts
and `TransitionPlan` SHALL remain derived. No Claim, Chronicle, Ledger, Campaign,
shared inbox, Lease, ref, task, or stored plan SHALL own normative intent or
reusable authority.

#### Scenario: Repository operation is represented

- **WHEN** ETHOS records a repository operation
- **THEN** the operation is expressible through Commitment, Attestation, Facts,
  and `TransitionPlan` without higher-layer semantic owners
- **AND** Attestations bind evidence without minting authority

#### Scenario: semantic attestation remains optional and bounded

- **WHEN** semantic assurance rather than digest-only proof is required
- **THEN** assurance is a candidate-external, non-authorizing Attestation bound
  to subject, scope, exact HEAD, verifier, verdict, and validity
- **AND** digest-only proof requires no external account or network

#### Scenario: Commitment is compiled, not stored

- **WHEN** ETHOS needs a Change's acceptance meaning
- **THEN** it compiles the Commitment from the exact Git-tree projection of the official OpenSpec Change
- **AND** no Commitment record, path, relation graph or workflow state is persisted
