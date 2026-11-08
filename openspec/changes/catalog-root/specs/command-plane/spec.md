## MODIFIED Requirements

### Requirement: Application operations have transport-independent meaning

CLI, SDK and MCP SHALL invoke the same typed application operations for status, planning, adoption,
integration and publication, selected through one catalog selection that refuses the same requests
alike. Transport adapters SHALL NOT parse CLI output, duplicate verdict rules or own repository
lifecycle state. Requests SHALL bind an explicit repository; results SHALL retain the existing
verdict, gaps, continuation and evidence boundaries.

#### Scenario: One observation is consumed through different transports

- **WHEN** CLI, SDK and MCP observe the same repository facts
- **THEN** their application verdict, gaps and continuation agree
- **AND** SDK invocation does not write stdout or change the process working directory

#### Scenario: A native capability fails after transport initialization

- **WHEN** a supported application operation cannot resolve a required native executable
- **THEN** CLI, SDK and MCP preserve the same typed blocking reason and root-bound failure evidence
- **AND** restoring that capability allows the same MCP instance to observe again
- **AND** transport adapters do not substitute generic protocol errors for known application
  failures

#### Scenario: A native Git observation times out

- **WHEN** a supported application operation receives a native Git observation timeout
- **THEN** its result is UNKNOWN with the original process evidence and an observation next action
- **AND** it does not claim a known repository state or authorize mutation replay

#### Scenario: Planning is consumed outside the CLI

- **WHEN** SDK or bound MCP clients request changed-scope or explicitly selected planning
- **THEN** they use the same current intent resolution, authority, gates and continuation as the CLI
- **AND** result composition does not import a CLI handler, write stdout or change the caller
  working directory

#### Scenario: An operation encounters an invalid-profile failure

- **WHEN** the repository profile owner rejects an operation's configuration
- **THEN** CLI, SDK and MCP retain the same blocking result and recovery guidance
- **AND** a transport does not replace the known failure with a generic protocol error
- **AND** adoption's authored-content conflicts retain their distinct operation-specific meaning

#### Scenario: Integration is consumed outside the CLI

- **WHEN** a bound SDK or MCP caller previews or applies integration
- **THEN** it invokes the same candidate, accepted or release operation as the CLI
- **AND** stale coordinates, missing authorization and required control verification retain their
  native refusal
- **AND** successful effects retain exact CAS and post-observation evidence without CLI rendering

#### Scenario: A client observes or retries completed accepted closeout

- **WHEN** the accepted and candidate refs, any required release mirror and their affected worktrees
  already satisfy closeout
- **THEN** preview and authorized retry report the same original effect identity through the
  existing Attestation owner, without creating another ref effect
- **AND** aligned bootstrap refs without an effect record remain an unattested no-op, not fabricated
  proof of an earlier transition
- **AND** ambiguous evidence or dirty affected worktrees cannot become successful recovery; current
  authorization and coordinate admission still apply

#### Scenario: Publication is consumed outside the CLI

- **WHEN** CLI, SDK or a bound MCP client previews or applies an exact publication receipt
- **THEN** all transports invoke the same publication application operation and native effect owners
- **AND** missing authorization, stale inputs and unknown observations retain their original refusal
- **AND** confirmed peer effects and independently admitted local retirement remain distinct
- **AND** direct SDK use does not write stdout or change the process working directory

#### Scenario: A request selects no catalog entry

- **WHEN** a CLI, SDK or MCP request's selectors match no root catalog entry, or it sets a field
  that its entry refuses
- **THEN** every transport returns the same `command_operation_unmatched` or `command_field_refused`
  result and executes nothing

### Requirement: The application package owns every shared operation

The status, planning, adoption, proof, integration and publication operations SHALL live in
`ethos.application`, select their catalog operation before they run and return typed results without
rendering them. The surfaces and `ethos.cli` SHALL NOT add imports of `domain`, `adapters`,
`repository`, `normalization` or `assistants`, and `domain` SHALL NOT add imports of `adapters`; the
import contracts list the remaining edges.

#### Scenario: Proof is reached as an application operation

- **WHEN** a caller invokes `prove_repository` with a repository and a proof request
- **THEN** its verdict, state, gaps and continuation equal those that `ethos prove --json` reports
  for the same request
- **AND** the call writes no stdout and raises no `SystemExit`
- **AND** a request that selects no proof operation returns the same refusal as `ethos prove --json`

#### Scenario: A surface adds an import of a lower layer

- **WHEN** a surface module imports `ethos.adapters`, `ethos.domain` or `ethos.repository` along an
  edge that the import contracts do not list
- **THEN** the import-boundaries gate fails

#### Scenario: A listed import is removed

- **WHEN** an edge that the import contracts list no longer exists
- **THEN** the import-boundaries gate fails until the list drops it

### Requirement: Governed transition commands fail closed on blocking verdicts

ETHOS transition commands that gate proof, land, or publish SHALL expose blocking verdicts through
both command JSON and process exit status 1, unless their catalog operation exits as an observation,
which exits 0 on every verdict. Any command SHALL exit 2 for a request that does not parse or
selects no operation, and 3 for a result it cannot deliver.

#### Scenario: gapped proof refuses through process status

- **WHEN** `ethos prove --expect-head <non-current-head> --json` runs
- **THEN** the JSON payload reports `verdict=block`
- **AND** the payload includes `expected_head_mismatch` in `required_gaps`
- **AND** the process exits with non-zero status

#### Scenario: A preview observes and its apply enforces

- **WHEN** `ethos land --closeout --json` and its apply with `--apply --authorize` both block
- **THEN** the preview exits 0 and the apply exits 1

#### Scenario: Usage and delivery failures exit apart from verdicts

- **WHEN** a root request selects no operation, sets a field its operation does not take or does not
  parse
- **THEN** the command exits 2 with a `usage_refused` result, as JSON under `--json`
- **AND** a result whose frame cannot be written exits 3

### Requirement: Public Command Plane

ETHOS SHALL keep the normal user workflow under six public commands: `ethos adopt`, `ethos status`,
`ethos plan`, `ethos prove`, `ethos land`, and `ethos publish`. Accepted-head admission is an exact
`ethos land --closeout` operation, not a seventh workflow command or a hidden Git-hook procedure.
The additional `ethos mcp --root <repo>` command SHALL launch a protocol transport over the same
application operations without creating lifecycle authority.

#### Scenario: Cyclopts exposes the terminal root surface

- **WHEN** the root CLI help is rendered
- **THEN** it exposes the six workflow commands and the MCP transport launcher
- **AND** `ethos status` is the single bounded reader
- **AND** maintainer mechanics remain hidden or semantically namespaced
- **AND** `ethos --help --json` prints the root operation catalog as one result within the declared
  `help` payload budget, and `ethos <command> --help --json` prints that command's part

#### Scenario: TransitionPlan is the single transition projection

- **WHEN** `ethos plan --json` compiles the current Commitment, repository facts, and declared nodes
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
  candidate head, receipt, plan digest and lease expiry), as `form` the catalog operation a root
  argv selects, empty for any other step, and why
- **AND** a root step's effects, destructiveness and authorization are its catalog operation's; for
  any other argv, the authorization is the strongest authority token in the argv (`attestation`,
  `confirm-irreversible`, `authorize` or `apply`), `none` without one, or `human` for a decision or
  an opaque step; the result schema also admits `delegation`, which no step emits yet
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
- **THEN** the schema-version-`3` result preserves `state` and `required_gaps`, exposes one
  `next_action`, and derives exactly one `continuation`: `continue`, `await-user`, `blocked`, or
  `done`
- **AND** `missing_facts_or_evidence` derives from `required_gaps` only when `verdict=unknown`,
  while `user_decision_required` names required judgment
- **AND** Continuation is recomputed rather than stored as lifecycle truth

#### Scenario: accepted closeout remediation is directly executable

- **WHEN** accepted-head admission is blocked by missing proof, missing external verification, stale
  coordinates, or an unapplied exact effect
- **THEN** status, plan, land, and hook projections SHALL expose the same single complete
  `ethos ...` command
- **AND** that command SHALL bind the current root, expected accepted HEAD, candidate HEAD, and any
  required receipt path
- **AND** it SHALL contain no prose-only instruction or placeholder token.

### Requirement: Continuation derives from explicit result facts

The schema-version-`3` result SHALL carry `user_decision_required` as an explicit typed fact
selected by the owning resolution. `continuation` SHALL be a pure projection from verdict, the
presence of the sole next action, and that fact. ETHOS SHALL NOT infer an authority boundary by
parsing command text, English phrases, or gap-name suffixes.

#### Scenario: A mutating-looking command is already authorized

- **WHEN** a result exposes an executable next action and explicitly states that no user decision is
  required
- **THEN** `user_decision_required` remains false
- **AND** Continuation is `continue` for a passing result or `blocked` for a non-passing result
- **AND** `next` names the step's write effects and the authorization it needs, so a harness can ask
  before it runs the step

#### Scenario: Human authority is required

- **WHEN** the owning resolution explicitly marks that handoff, authorization, or confirmation is
  required
- **THEN** `user_decision_required` is true
- **AND** Continuation is `await-user` without inspecting the action string or gap spelling
- **AND** `next` is a `decision` with authorization `human`, which carries the argv a person
  approves when the action is one exact ETHOS argv

### Requirement: The structured next step derives from the exact rendered argv

ETHOS SHALL derive `next` only from the exact ETHOS argv that `next_action` renders, by a lossless
split and join, and SHALL take its effects, authorization and destructiveness from the catalog
operation a root argv selects, or from the admission classification of any other argv. Prose or a
template SHALL stay an instruction without an argv. Every reader SHALL re-derive `next` and check a
carried one only for shape.

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
  retirement apply, a `publish --retire` apply, `attestation release` or a `land --retag` apply
- **THEN** `next.destructive` is true

#### Scenario: An opaque step needs a person

- **WHEN** `next_action` is `ethos host run` or `ethos mcp`, whose argv cannot bound what it runs
- **THEN** `next` reports the `opaque` effect, `destructive` true and authorization `human`

#### Scenario: A root argv selects no operation

- **WHEN** `next_action` is a root argv whose flags select no catalog operation, or set a field its
  operation does not take
- **THEN** `next` reports the `opaque` effect, `destructive` true, authorization `human` and an
  empty `form`

#### Scenario: Hook admission keeps its readers

- **WHEN** hook admission classifies an ETHOS argv
- **THEN** only `status` and `plan` without a mutating token are read-only, whatever `next` reports
  for the same argv

### Requirement: Cyclopts And API Own Interface Semantics

The root operation catalog SHALL declare the root commands' names, parameters, help and selection
once; Cyclopts SHALL render them and own the group commands, and the in-process operation API SHALL
select through the same catalog. ETHOS SHALL NOT maintain a parallel command registry, lazy
report-handler DSL, re-export facade, or command-shaped quality plane.

#### Scenario: A command signature changes

- **WHEN** a public operation changes its parameters or help
- **THEN** CLI, SDK metadata, generated docs, and protocol projections derive from the same
  operation declaration
- **AND** a root operation's keyword signature that differs from its request model fails the catalog
  table test

#### Scenario: ETHOS runs from an installed wheel

- **WHEN** the package runs outside a source checkout
- **THEN** packaged lifecycle and gate resources remain available
- **AND** command discovery still comes from the catalog and Cyclopts declarations, not a packaged
  command registry

### Requirement: CLI Surface Delegation

The CLI SHALL compose output and UX while delegating semantics to contracts, operations, repository
policy, and adapters; one generic adapter SHALL derive the root commands from the operation catalog.

#### Scenario: CLI package is scanned

- **WHEN** architecture tests inspect imports
- **THEN** command modules call concrete operation and adapter owners
- **AND** no command registry besides the operation catalog, no generic report compiler and no CLI
  subprocess loopback exists

### Requirement: Publish is the sole remote Git object projection command

`ethos publish` SHALL alone compile, persist and apply remote Git object effects. It SHALL select
typed targets from positive repository topology; bind exact local objects and proof Attestations;
persist one content-addressed request, applied only by its receipt; recheck all targets before
effects; apply peer-local exact CAS; and attest partial or complete results in machine-readable
form. Tags and protected branches SHALL be modes of this command, not separate commands or hook
exceptions.

#### Scenario: dry-run creates one immutable request

- **WHEN** a caller requests remote projection with exact local and peer facts
- **THEN** `ethos publish` SHALL return the request path, digest, source object, targets, proof, and
  exact apply command
- **AND** it SHALL perform no remote mutation

#### Scenario: apply consumes the same request

- **WHEN** request bytes and all bound coordinates remain current
- **THEN** `ethos publish --receipt ... --apply --authorize` SHALL execute only the request's
  effects
- **AND** it SHALL reject any repository, object, proof, ref, peer, or expected-OID drift

#### Scenario: A retirement receipt shows its deletion

- **WHEN** a request retires peer refs
- **THEN** its apply command carries `--retire`, and `next` reports it as destructive
- **AND** applying a retirement request without `--retire`, or a publication request with it,
  refuses with `remote_publication_receipt_retire_mismatch` before any peer effect

#### Scenario: missing proof is actionable

- **WHEN** the selected local object lacks the required exact proof Attestation
- **THEN** publish and pre-push SHALL report the same proof gap
- **AND** both SHALL identify `ethos prove --execute --expect-head <oid> --json` as the sole
  continuation

#### Scenario: An apply without a receipt selects nothing

- **WHEN** `ethos publish --apply` runs without `--receipt`, with or without `--ref`, `--peer` or
  `--retire`, or the MCP `publish` tool applies without a receipt
- **THEN** it refuses with `command_operation_unmatched:publish` before any observation
- **AND** the probe of the same refs persists the request whose receipt apply is its `next`
