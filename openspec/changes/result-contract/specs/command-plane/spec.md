## MODIFIED Requirements

### Requirement: Public Command Plane

ETHOS SHALL keep the normal user workflow under six public commands:
`ethos adopt`, `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and
`ethos publish`. Accepted-head admission is an exact `ethos land --closeout`
operation, not a seventh workflow command or a hidden Git-hook procedure.
The additional `ethos mcp --root <repo>` command SHALL launch a protocol transport
over the same application operations without creating lifecycle authority.

#### Scenario: Cyclopts exposes the terminal root surface

- **WHEN** the root CLI help is rendered
- **THEN** it exposes the six workflow commands and the MCP transport launcher
- **AND** `ethos status` is the single bounded reader
- **AND** maintainer mechanics remain hidden or semantically namespaced

#### Scenario: TransitionPlan is the single transition projection

- **WHEN** `ethos plan --json` compiles the current Commitment, repository
  facts, and declared nodes
- **THEN** it returns one deterministic `transition_plan`
- **AND** no parallel workflow-runtime or domain-contract read model is emitted

#### Scenario: Default payloads stay bounded

- **WHEN** any command's JSON result would exceed its declared default payload budget
- **THEN** the command preserves `verdict`, `state`, `summary`, `required_gaps`, `next`,
  `next_action`, `continuation`, `missing_facts_or_evidence`, and `user_decision_required`
- **AND** each failing step's id, exit code and first 20 output lines stay inline, with counts of
  what was omitted
- **AND** oversized detail moves to a digest-bound artifact that `data.detail` names, while the
  command's own small entries, such as receipts, paths and evidence references, stay inline
- **AND** a result that would still exceed its budget is truncated with counts, never refused
- **AND** no alternate reader command or truth source is introduced

#### Scenario: The next step is structured data

- **WHEN** a result selects a next step
- **THEN** `next` carries the step's argv, its effects (`read`, `local-evidence-write`,
  `local-write`, `remote-read` or `remote-write`), whether its authorization is embedded or
  requires a human, its binding (head, plan digest, receipt and lease generation, when present)
  and why
- **AND** `next_action` renders the same step for humans
- **AND** a step that needs a human decision carries no argv

#### Scenario: A result names its runtime

- **WHEN** any command returns a result
- **THEN** the result names the product version, source commit and runtime id that produced it

#### Scenario: a reader derives continuation

- **WHEN** current authoritative facts are sufficient to select the next boundary
- **THEN** the schema-version-`2` result preserves `state` and `required_gaps`,
  exposes one `next_action`, and derives exactly one `continuation`: `continue`,
  `await-user`, `blocked`, or `done`
- **AND** `missing_facts_or_evidence` derives from `required_gaps` only when
  `verdict=unknown`, while `user_decision_required` names required judgment
- **AND** Continuation is recomputed rather than stored as lifecycle truth

#### Scenario: accepted closeout remediation is directly executable

- **WHEN** accepted-head admission is blocked by missing proof, missing external
  verification, stale coordinates, or an unapplied exact effect
- **THEN** status, plan, land, and hook projections SHALL expose the same single
  complete `ethos ...` command
- **AND** that command SHALL bind the current root, expected accepted HEAD,
  candidate HEAD, and any required receipt path
- **AND** it SHALL contain no prose-only instruction or placeholder token.
