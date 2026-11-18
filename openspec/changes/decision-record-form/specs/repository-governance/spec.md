## ADDED Requirements

### Requirement: Accepted decision records are kept in one form

An accepted decision record SHALL be kept: it SHALL NOT be removed from its decisions directory,
and a changed ruling SHALL be a new record that names the record it supersedes or updates. Every
governed repository SHALL write its decision records in the one form that the Docs Registry
states.

#### Scenario: A record no longer governs

- **WHEN** a later record replaces an accepted record's ruling, or its subject is gone
- **THEN** the record stays in its decisions directory under its number
- **AND** the later record declares whether it supersedes the record or updates a part of it
- **AND** a record that a later record updates in part carries a mark at each replaced or
  extended sentence or list item, and that sentence or list item is updated once

#### Scenario: A Change removes a decision record

- **WHEN** a Change deletes a decision record from a decisions directory
- **THEN** its review refuses the deletion

## MODIFIED Requirements

### Requirement: Minimal Decision Rationale Preservation

ETHOS SHALL admit a decision record only when its choice among alternatives, its consequences and
its revisit condition remain useful across more than one Change and the current semantic owner
cannot carry them. A record explains why; it SHALL NOT own current product behavior or workflow
state. Its positive four-digit number SHALL remain stable and SHALL NOT be reused for a different
ruling. Its semantic topic MAY change with repaired links.

#### Scenario: Historical decision material is evaluated

- **WHEN** a decision record that an earlier Change removed exists only in Git's history
- **THEN** the index of the decisions directory keeps a row for its number that names the commit
  and the path where Git holds it
- **AND** the record returns to the directory as it last was, marked, once the repository's
  engine reads the status that it then carries

#### Scenario: Decision rationale uses the minimum physical shape

- **WHEN** more than one decision rationale is retained under `docs/decisions/`
- **THEN** `dr-<four-digit-id>-<semantic-topic>.md` records remain directly navigable from
  `docs/decisions/README.md`, which explains the directory's role
- **AND** `docs/README.md` routes readers to that entrance instead of copying
  the record list
- **AND** the entrance is the index of the directory: one table with a row for each number from
  one to the highest, which holds no rule text
- **AND** the entrance is not a runtime authority, or a reason to add a template, a lifecycle
  directory, a companion page or a duplicate catalog

#### Scenario: Decision identity is missing or duplicated

- **WHEN** a `role: decision` record in the selected documentation root has no
  stable numbered filename or shares its number with another current record
- **THEN** the Docs Registry blocks that exact source or conflicting pair
- **AND** a historical retired number is never assigned to a different ruling;
  current-tree uniqueness alone does not establish that historical fact

#### Scenario: Current authority is resolved

- **WHEN** a reader opens a decision record
- **THEN** it identifies the current semantic owner
- **AND** current behavior is determined by that owner, not historical rationale

#### Scenario: Decision identity and disposition agree across native carriers

- **WHEN** the Docs Registry reads a `role: decision` document under any selected root
- **THEN** its filename, `decision_id`, and sole document-level title identify the same positive
  ruling
- **AND** `decision_status: accepted` and `state: canonical` distinguish decision disposition from
  document classification without claiming implementation acceptance or authority
- **AND** malformed metadata, duplicate identities and contradictory carriers block without mutating
  source

#### Scenario: Rationale remains distinct from an execution procedure

- **WHEN** a decision record is validated through the shared native documentation owner
- **THEN** its only sections are Context, Decision, Alternatives Rejected, Consequences and
  Boundary, and Evidence and Revisit, in that order, each with readable rationale
- **AND** ordinary prose, rationale lists, quotations, tables, bare paths and evidence links remain
  valid
- **AND** task progress, code blocks, extra HTML, nested or extra headings and executable procedures
  cannot impersonate decision rationale
- **AND** syntax inspection never evaluates commands or ambient variables, preserves unresolved
  invocation ambiguity, and does not certify decision quality or current delivery
- **AND** ETHOS's own retained rationale migrates to the same form without losing alternatives,
  costs, boundaries, historical dates, evidence or revisit conditions

### Requirement: Singular Documentation Entrypoint

ETHOS SHALL expose `docs/README.md` as its sole current documentation
entrypoint.

#### Scenario: Current documentation is traversed

- **WHEN** a current source, policy, or documentation carrier links to the
  documentation entrypoint
- **THEN** it SHALL link to `docs/README.md`
- **AND** `docs/index.md` SHALL be absent
- **AND** immutable historical evidence MAY retain the path observations that
  were true when it was recorded.

#### Scenario: An adopter uses the portable Docs Registry

- **WHEN** ETHOS audits an adopted repository
- **THEN** the adopter SHALL NOT be required to reproduce ETHOS's root documentation filename
- **AND** an adopter that keeps decision records keeps them in the `decisions` directory of its
  documentation home, in the form that the Docs Registry states
- **AND** portable subject, role, state, and relation semantics SHALL remain the
  shared contract.
