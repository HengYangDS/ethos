## MODIFIED Requirements

### Requirement: Native Documentation Topology

ETHOS SHALL organize governed documentation by function and authority rather
than by `current`/`future` directory names, and SHALL use one explicit rule for
documentation roots, onboarding placement, and README necessity. The physical
shape of ETHOS's own docs is a product projection; adopter repositories retain
their native subject layout under the portable Docs Registry contract.

#### Scenario: Common docs kernel is audited

- **WHEN** documentation governance audits the repository
- **THEN** it requires only the common semantic kernel owned by the current
  contract: the documentation root, evidence, history, and reference lanes
- **AND** product extension roots are retained only when they contain a distinct
  subject or function
- **AND** no extension root is mandatory for an adopter merely because ETHOS
  uses it

#### Scenario: First-run guidance is placed by function

- **WHEN** ETHOS has one first-run onboarding document
- **THEN** it SHALL live under the `guides` function root as `docs/guides/quickstart.md`
- **AND** links, stable-path metadata, taxonomy metadata, registry output, and
  command examples SHALL resolve to that path
- **AND** the former onboarding root SHALL not remain as a historical habit or
  redirect root

#### Scenario: A documentation directory needs a README

- **WHEN** a documentation directory is evaluated for a README
- **THEN** a README SHALL exist only when it provides real navigation, a
  semantic boundary, or an index for multiple meaningful children
- **AND** a directory with one substantive document SHALL not receive a
  placeholder README merely because the directory exists
- **AND** an empty directory or `.gitkeep` SHALL be removed

#### Scenario: Documentation taxonomy is projected

- **WHEN** the Docs Registry reads the ETHOS documentation tree
- **THEN** role, state, subject, and relation metadata are validated by the
  registry owner and directory names express subject/function rather than
  lifecycle state
- **AND** the registry SHALL report every broken link, stale stable path,
  unindexed document, duplicate subject, and invalid README disposition

#### Scenario: `current`/`future` roots do not become truth lanes

- **WHEN** ETHOS audits docs topology or scaffolds an adopted repository
- **THEN** ETHOS does not require physical `current` or `future` roots, and does
  not accept `current` or `future` as documentation state values
- **AND** present repository truth is proven by HEAD, authority order,
  contracts, evidence, claims, and proof rather than by directory name
- **AND** unlanded intent belongs in OpenSpec changes, plans, research, or
  decision revisit triggers rather than in a generic intent directory

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, guides, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes

### Requirement: Continuous intent preserves bounded Changes

Every accepted feedback occurrence SHALL be preserved in the Attestation set
and selected to a semantic owner or explicit absence, contradiction, or
model-gap disposition. New input SHALL NOT expand an active Change implicitly.
Topology convergence SHALL not create or preserve a second carrier for Change
lineage, predecessor/successor meaning, hypothesis, experiment,
requirement-coverage, or scope/granularity semantics. Existing authoritative
owners remain the only sources; a missing public derived view SHALL be recorded
as a separate model gap rather than fabricated by this Change.

#### Scenario: Several agents provide concurrent feedback

- **WHEN** their inputs are independent
- **THEN** exact-CAS set union preserves every occurrence
- **AND** selections may feed disjoint future official OpenSpec Changes

#### Scenario: A Change's scope or granularity is evaluated

- **WHEN** a proposed obligation is considered for an active Change
- **THEN** it is admitted only when its intent, implementation, proof, and
  closeout form one reviewable outcome
- **AND** unrelated intent becomes a separate official Change or a
  non-authorizing Attestation rather than expanding the active Change

#### Scenario: Lineage and experimental reasoning are audited

- **WHEN** topology convergence audits predecessors, successors, hypotheses,
  experiments, or requirement coverage
- **THEN** it identifies the existing source owner and whether a public derived
  view is actually available
- **AND** it does not create a mutable Change DAG, hypothesis registry,
  experiment ledger, successor back-link, or replacement carrier when that view
  is absent
