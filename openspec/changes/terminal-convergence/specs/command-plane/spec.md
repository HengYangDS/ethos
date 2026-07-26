## ADDED Requirements

### Requirement: Singular Lifecycle Surface
The public lifecycle MUST be `status -> plan -> prove -> land -> publish`; status MUST contain first-glance orientation facts and no independent quality_summary or orient command may own readiness semantics.

#### Scenario: A caller requests repository readiness
- **WHEN** the caller invokes status
- **THEN** it receives role, authority, gaps, coordination facts, and next actions from the same verdict owner used by the transition commands

### Requirement: Compact Truthful Output
Default command JSON MUST include verdict, summary, gaps, next actions, and artifact references only; status MUST be at most 16 KiB and plan at most 32 KiB for the reference repository fixtures.

#### Scenario: Diagnostic detail exceeds the payload budget
- **WHEN** a command has verbose facts larger than its default payload limit
- **THEN** it writes or identifies a digest-bound artifact and returns a reference instead of embedding the detail

### Requirement: Hard Gaps Cannot Be Green
A hard policy gap MUST force `ok=false`, a blocking or unknown verdict, and non-ready lifecycle summaries.

#### Scenario: Source budget is above the terminal maximum
- **WHEN** current measurement exceeds a hard source budget
- **THEN** status, prove, land, and publish cannot report ready, closed-loop, perfect, or successful states

### Requirement: PlanIR Owns Transition Projection
Plan and proof MUST bind one explicitly selected ChangeContract whenever more
than one active contract exists. External node requirements MUST be present in
repository facts or block the PlanIR.

#### Scenario: Multiple active ChangeContracts exist
- **WHEN** proof is requested without a Change selector
- **THEN** it reports `change_contract_ambiguous`
- **AND** `ethos prove --change <id>` binds the selected ID into the PlanIR digest
