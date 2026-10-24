## MODIFIED Requirements

### Requirement: Native Documentation Topology

ETHOS SHALL organize governed documentation by function and authority rather
than by `current`/`future` directory names, and SHALL use one explicit rule for
documentation roots, onboarding placement, and README necessity. The physical
shape of ETHOS's own docs is a product projection; adopter repositories retain
their native subject layout under the portable Docs Registry contract.

#### Scenario: Common docs kernel is audited

- **WHEN** documentation governance audits the repository
- **THEN** it checks declared subjects, purposes, authority and reachable
  relationships without requiring evidence or lifecycle directories
- **AND** product roots remain only for distinct subject responsibilities
- **AND** retained evidence follows its producer, consumer, binding and lifetime
- **AND** no ETHOS extension root is mandatory for an adopter

#### Scenario: First-run guidance is placed by function

- **WHEN** ETHOS has one first-run onboarding document
- **THEN** it SHALL live under the `guides` function root as `docs/guides/quickstart.md`
- **AND** links, stable-path metadata, taxonomy metadata, registry output, and
  command examples SHALL resolve to that path
- **AND** the former onboarding root SHALL not remain as a historical habit or
  redirect root

#### Scenario: A documentation directory needs a README

- **WHEN** a documentation directory is evaluated for a README
- **THEN** two or more immediate navigable children SHALL have a README
  with a local route into the directory's content
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
- **AND** proposed behavior and acceptance belong in the selected official
  Change; plans, research and revisit conditions supply linked context only
- **AND** no generic intent directory becomes a second change authority

#### Scenario: Product pseudo-lanes do not become common kernel

- **WHEN** ETHOS reports product extension roots
- **THEN** architecture, concepts, governance, plans, research, guides, and
  metadata roots may appear as product extensions
- **AND** contract and evolution labels do not become mandatory replacement
  roots for the removed `current`/`future` lanes

#### Scenario: Declared normative documentation has a reader route

- **WHEN** the repository declares normative sources inside its configured documentation root
- **THEN** each declared source is reachable from that root's registered README through actual local Markdown links
- **AND** reference links and intermediate directory READMEs remain valid routes, cycles terminate, and fenced examples do not become navigation
- **AND** missing routes are reported without absorbing sources outside the documentation root or changing source bytes

### Requirement: Minimal Decision Rationale Preservation

ETHOS SHALL retain a decision record only when deleting it would erase
cross-Change rationale not carried by the current semantic owner. A record
explains why; it SHALL NOT own current product behavior or workflow state.
Its positive four-digit number SHALL remain stable and SHALL NOT be reused for
a different ruling. Its semantic topic MAY change with repaired links.

#### Scenario: Historical decision material is evaluated

- **WHEN** a removed decision subsystem contains rationale from several files
- **THEN** semantically distinct alternatives, consequences and revisit
  conditions are retained; overlapping or fully absorbed records are removed

#### Scenario: Decision rationale uses the minimum physical shape

- **WHEN** more than one decision rationale is retained under `docs/decisions/`
- **THEN** `dr-<four-digit-id>-<semantic-topic>.md` records remain directly navigable from
  `docs/decisions/README.md`, which explains the directory's role
- **AND** `docs/README.md` routes readers to that entrance instead of copying
  the record list
- **AND** the entrance is not a decision registry, runtime authority, or
  reason to add a template, schema, lifecycle directory, or duplicate catalog

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
- **THEN** its filename, `decision_id`, and sole document-level title identify the same positive ruling
- **AND** `decision_status: accepted` and `state: canonical` distinguish decision disposition from document classification without claiming implementation acceptance or authority
- **AND** malformed metadata, duplicate identities and contradictory carriers block without mutating source

#### Scenario: Rationale remains distinct from an execution procedure

- **WHEN** a decision record is validated through the shared native documentation owner
- **THEN** its only sections are Context, Decision, Alternatives Rejected, Consequences and Boundary, and Evidence and Revisit, in that order, each with readable rationale
- **AND** ordinary prose, rationale lists, quotations, tables, bare paths and evidence links remain valid
- **AND** task progress, code blocks, extra HTML, nested or extra headings and executable procedures cannot impersonate decision rationale
- **AND** syntax inspection never evaluates commands or ambient variables, preserves unresolved invocation ambiguity, and does not certify decision quality or current delivery
- **AND** ETHOS's own retained rationale migrates to the same form without losing alternatives, costs, boundaries, historical dates, evidence or revisit conditions
