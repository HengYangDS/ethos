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
- **AND** `data` keeps the command's own small entries, such as receipts, paths and evidence
  references, and the scalar fields of a larger mapping
- **AND** a top-level `bound` names the digest-bound detail artifact of the full result, each
  failing step's id, exit code and first 20 output lines, and the entries it shortened or moved,
  with counts of what was omitted
- **AND** detail older than seven days is removed whenever new detail is written
- **AND** detail is a cache, not an effect: when it cannot be written, the result stays inline,
  names the reason in `bound.detail_unavailable`, and still fits
- **AND** a result that would still exceed its budget is truncated with counts, never refused
- **AND** no alternate reader command or truth source is introduced

#### Scenario: The next step is structured data

- **WHEN** a result selects a next step
- **THEN** `next` names its kind (`command`, `instruction`, `decision` or `done`), and a `command`
  carries the exact ETHOS argv, its effects ordered from `read`, `remote-read`, `execute`,
  `local-evidence-write` and `local-write` to `remote-write`, whether running it embeds an
  authorization, the values its flags bind (root, head, candidate head, receipt, plan digest and
  lease expiry) and why
- **AND** `next_action` renders the same step for humans
- **AND** a step that needs a human decision carries no argv

#### Scenario: A result names its runtime

- **WHEN** any command returns a JSON result
- **THEN** `summary.runtime` names the product version, distribution version and source commit of
  the committed build that produced it

#### Scenario: a reader derives continuation

- **WHEN** current authoritative facts are sufficient to select the next boundary
- **THEN** the schema-version-`3` result preserves `state` and `required_gaps`,
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

### Requirement: Continuation derives from explicit result facts

The schema-version-`3` result SHALL carry `user_decision_required` as an explicit typed fact
selected by the owning resolution. `continuation` SHALL be a pure projection from verdict, the
presence of the sole next action, and that fact. ETHOS SHALL NOT infer an authority boundary by
parsing command text, English phrases, or gap-name suffixes. The structured `next` step SHALL be
derived only from the exact ETHOS argv that `next_action` renders, by a lossless split and join;
its effects come from the admission classification of that argv, and prose or a template stays an
instruction without an argv.

#### Scenario: A mutating-looking command is already authorized

- **WHEN** a result exposes an executable next action and explicitly states that no user decision
  is required
- **THEN** `user_decision_required` remains false
- **AND** Continuation is `continue` for a passing result or `blocked` for a non-passing result
- **AND** `next` names the argv's write effects and an `embedded` authorization, so a harness can
  ask before it runs the step

#### Scenario: Human authority is required

- **WHEN** the owning resolution explicitly marks that handoff, authorization, or confirmation is
  required
- **THEN** `user_decision_required` is true
- **AND** Continuation is `await-user` without inspecting the action string or gap spelling
- **AND** `next` is a `decision` with no argv
