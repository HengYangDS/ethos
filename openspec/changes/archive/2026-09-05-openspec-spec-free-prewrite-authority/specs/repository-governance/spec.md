## MODIFIED Requirements

### Requirement: Official spec-free Changes compile acceptance

ETHOS SHALL compile deterministic non-empty acceptance for an official OpenSpec
Change that explicitly declares `skip_specs: true`, contains no requirement
deltas, and has a complete planning artifact graph. The acceptance SHALL use
only official OpenSpec projection facts, SHALL preserve the semantic content of
metadata, proposal, design, and task descriptions, and SHALL exclude task
checkbox progress. ETHOS SHALL NOT require completed implementation tasks, fake
requirements, `commitment.toml`, or another tracked intent carrier before
bounded implementation writes can be admitted.

#### Scenario: Planned spec-free Change is selected before implementation

- **GIVEN** the official OpenSpec projection declares `skip_specs: true`
- **AND** its required proposal, design, and tasks artifacts are present and valid
- **AND** it contains no requirement deltas
- **AND** one or more implementation tasks remain incomplete
- **WHEN** ETHOS compiles the selected Change
- **THEN** it produces one deterministic non-empty transient Commitment
- **AND** that Commitment can authorize bounded implementation paths through the ordinary current resolver.

#### Scenario: Task progress does not mutate acceptance identity

- **GIVEN** a valid spec-free Change whose task descriptions are unchanged
- **WHEN** task checkboxes advance from incomplete to complete
- **THEN** the compiled Commitment digest remains unchanged
- **AND** OpenSpec task progress remains available independently for proof and closeout admission.

#### Scenario: Completed spec-free Change is selected

- **GIVEN** a valid spec-free Change whose required tasks are complete
- **WHEN** ETHOS proves and archives the selected Change
- **THEN** its Commitment remains applicable through the attested official archive transition
- **AND** closeout does not reconstruct authority from archived task progress.

#### Scenario: Empty deltas are not implicitly accepted

- **WHEN** a Change has no requirement deltas but lacks the official spec-free declaration or a complete valid planning artifact graph
- **THEN** ETHOS fails closed with the exact OpenSpec acceptance gap
- **AND** no filename pattern, product category, compatibility carrier, task progress state, or archived directory grants authority.
