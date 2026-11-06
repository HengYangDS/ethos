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
  `local-evidence-write`, `local-write` and `host-write` to `remote-write` and the unbounded
  `opaque`, whether it is destructive, its authorization, the values its flags bind (root, head,
  candidate head, receipt, plan digest and lease expiry), an empty `form` and why
- **AND** the authorization is the strongest authority token in the argv (`attestation`,
  `confirm-irreversible`, `authorize` or `apply`), `none` without one, or `human` for a decision or
  an opaque step
- **AND** `destructive` says whether the argv selects the deletion of something it does not
  recreate; cleanup that another operation performs under a liveness check is not counted, and that
  operation reports it in its result
- **AND** `next_action` renders the same step for humans
- **AND** a decision whose text is one exact ETHOS argv carries that argv, its effects,
  `destructive` and binding, with authorization `human`: the argv is what a person approves, and no
  reader runs it without that approval

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

### Requirement: Candidate ref movement is proof-bound

Candidate ref movement SHALL be protected by executed proof bound to the new
candidate head, just like accepted-root closeout.

#### Scenario: raw candidate ref update lacks executed proof

- **WHEN** a ref update attempts to move `candidate/dev` without sanctioned ETHOS
  land semantics and executed proof for the new head
- **THEN** the reference-transaction admission blocks the ref movement
- **AND** sanctioned land may proceed only through the explicit ETHOS ref-move
  allowance after its own proof checks

#### Scenario: official candidate refresh carries scoped ref-move context

- **WHEN** `ethos lane candidate --refresh-from-accepted --apply --authorize`
  resets a clean candidate worktree to the accepted root under an armed
  reference-transaction hook
- **THEN** the reset carries the scoped official ref-move allowance
- **AND** the command still requires `--expect-head` and reports
  `candidate_refresh_from_accepted_failed` if the reset fails

#### Scenario: A refresh that would drop candidate commits needs confirmation

- **WHEN** `ethos lane candidate --refresh-from-accepted --apply --authorize` would move a candidate
  head that the accepted branch does not contain
- **THEN** it refuses with `candidate_refresh_unaccepted_commits` before any ref effect
- **AND** its next action is the same command with `--confirm-irreversible`, for a person to
  approve, and that form is destructive

### Requirement: Publish is the sole remote Git object projection command

`ethos publish` SHALL alone compile, persist and apply remote Git object effects.
It SHALL select typed targets from positive repository topology; bind exact local
objects and proof Attestations; persist one content-addressed request; recheck
all targets before effects; apply peer-local exact CAS; and attest partial or
complete results in machine-readable form. Tags and protected branches SHALL be
modes of this command, not separate commands or hook exceptions.

#### Scenario: dry-run creates one immutable request

- **WHEN** a caller requests remote projection with exact local and peer facts
- **THEN** `ethos publish` SHALL return the request path, digest, source object, targets, proof, and exact apply command
- **AND** it SHALL perform no remote mutation

#### Scenario: apply consumes the same request

- **WHEN** request bytes and all bound coordinates remain current
- **THEN** `ethos publish --receipt ... --apply --authorize` SHALL execute only the request's effects
- **AND** it SHALL reject any repository, object, proof, ref, peer, or expected-OID drift

#### Scenario: A retirement receipt shows its deletion

- **WHEN** a request retires peer refs
- **THEN** its apply command carries `--retire`, and `next` reports it as destructive
- **AND** applying a retirement request without `--retire`, or a publication request with it,
  refuses with `remote_publication_receipt_retire_mismatch` before any peer effect

#### Scenario: missing proof is actionable

- **WHEN** the selected local object lacks the required exact proof Attestation
- **THEN** publish and pre-push SHALL report the same proof gap
- **AND** both SHALL identify `ethos prove --execute --expect-head <oid> --json` as the sole continuation

### Requirement: Continuation derives from explicit result facts

The schema-version-`3` result SHALL carry `user_decision_required` as an explicit typed fact
selected by the owning resolution. `continuation` SHALL be a pure projection from verdict, the
presence of the sole next action, and that fact. ETHOS SHALL NOT infer an authority boundary by
parsing command text, English phrases, or gap-name suffixes.

#### Scenario: A mutating-looking command is already authorized

- **WHEN** a result exposes an executable next action and explicitly states that no user decision
  is required
- **THEN** `user_decision_required` remains false
- **AND** Continuation is `continue` for a passing result or `blocked` for a non-passing result
- **AND** `next` names the argv's write effects and its strongest authority token, so a harness
  can ask before it runs the step

#### Scenario: Human authority is required

- **WHEN** the owning resolution explicitly marks that handoff, authorization, or confirmation is
  required
- **THEN** `user_decision_required` is true
- **AND** Continuation is `await-user` without inspecting the action string or gap spelling
- **AND** `next` is a `decision` with authorization `human`, which carries the argv a person
  approves when the action is one exact ETHOS argv

### Requirement: The structured next step derives from the exact rendered argv

ETHOS SHALL derive `next` only from the exact ETHOS argv that `next_action` renders, by a lossless
split and join, and SHALL take its effects, authorization and destructiveness from the admission
classification of that argv. Prose
or a template SHALL stay an instruction without an argv. Every reader SHALL re-derive `next` and
check a carried one only for shape.

#### Scenario: A rendered command becomes a structured step

- **WHEN** a result's `next_action` is one exact ETHOS argv
- **THEN** `next` carries that argv, its effects, its authorization and the values its flags bind

#### Scenario: Prose stays an instruction

- **WHEN** a result's `next_action` is prose, a template with a placeholder, or another tool's
  command
- **THEN** `next` is an `instruction` with no argv

#### Scenario: A reader never trusts a carried step

- **WHEN** a reader validates a payload whose `next` differs from its own derivation
- **THEN** it keeps its own derivation, and refuses the payload only when the carried `next` is
  malformed

#### Scenario: A deleting argv is destructive

- **WHEN** `next_action` selects the deletion of something the command does not recreate, such as a
  retirement apply, `publish --retire`, `attestation release` or `land --retag`
- **THEN** `next.destructive` is true

#### Scenario: An opaque step needs a person

- **WHEN** `next_action` is `ethos host run` or `ethos mcp`, whose argv cannot bound what it runs
- **THEN** `next` reports the `opaque` effect, `destructive` true and authorization `human`

#### Scenario: Hook admission keeps its readers

- **WHEN** hook admission classifies an ETHOS argv
- **THEN** only `status` and `plan` without a mutating token are read-only, whatever `next` reports
  for the same argv
