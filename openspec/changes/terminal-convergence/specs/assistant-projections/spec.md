## MODIFIED Requirements

### Requirement: Projection Boundary
Collaboration and handoff SHALL be vendor-neutral projections over selected Commitments, fresh Facts, and Attestations; no host transcript or session state owns repository truth.

#### Scenario: projection drift is audited

- **WHEN** `ethos prove --gate playbooks-v2 --json` runs
- **THEN** ETHOS reports package, registry, generator, and projection drift
  records without accepting host metadata as authority

#### Scenario: official workflow projects agent-native entry points

- **WHEN** a complete adopter initializes or updates an admitted agent host
- **THEN** the pinned official OpenSpec workflow generates that host's Skills
  and supported slash commands from its resolved schema and workflow templates
- **AND** generated artifacts identify OpenSpec 1.8.0 and consume official
  `status` and `instructions` output rather than hardcoded artifact names
- **AND** ETHOS carries no copied OpenSpec template or second lifecycle owner

#### Scenario: the skill portfolio evolves without parallel truth

- **WHEN** an ETHOS skill route is admitted, evaluated, replaced, or retired
- **THEN** coverage, overlap, novelty, route ownership, package quality, and
  retirement checks report one active subject-operation owner
- **AND** retirement removes the obsolete carrier and records its reason, date,
  and kill signal
- **AND** matched evaluation remains evidence metadata and cannot own tasks,
  progress, status, completion, or lifecycle
- **AND** Superpowers and other method packs remain optional procedures

#### Scenario: a different agent takes over
- **WHEN** an agent host changes
- **THEN** the successor consumes the same bounded handoff projection without replaying private session state

#### Scenario: an actor is referenced across hosts
- **WHEN** a lease, handoff, takeover, receipt, or Attestation names an actor
- **THEN** it uses a vendor-neutral actor reference with explicit kind, namespace,
  stable subject, and local proof basis
- **AND** provider usernames, model names, session IDs, process IDs, and display
  labels remain projections or observations and do not mint authority
- **AND** an unavailable or ambiguous actor binding remains `unknown` and blocks
  effects that require identity

### Requirement: Terminal assistant projections are derived, not root configuration
Optional protocol adapters SHALL consume the kernel and remain replaceable; they SHALL not introduce a repository truth root.

#### Scenario: A repository is scaffolded or parity-checked

- **WHEN** ETHOS renders the current adopter scaffold or checks its manifest
- **THEN** `.ethos/assistants.toml` is absent from required artifacts
- **AND** assistant projection behavior continues to come from canonical source
  and activation contracts.

#### Scenario: The product removes the retired projection file

- **WHEN** the product checkout no longer contains `.ethos/assistants.toml`
- **THEN** projection checks and assistant tests remain valid
- **AND** no runtime consumer treats the removed file as required truth.

#### Scenario: a protocol adapter is removed
- **WHEN** a protocol adapter is uninstalled
- **THEN** the selected Commitment, Attestations, and other projections remain usable

#### Scenario: an execution substrate is evaluated
- **WHEN** an agent host, durable runtime, method pack, or graph executor is proposed
- **THEN** it proves pause, resume, handoff, authority isolation, uninstall
  cleanliness, zero repository shadow state, and a measured token or elapsed-time gain
- **AND** absence of that substrate leaves the native lifecycle complete.

#### Scenario: execution consumes a bounded budget
- **WHEN** an agent host, model tier, concurrent worker set, or optional execution
  substrate performs governed work
- **THEN** progress is credited only when an unsatisfied acceptance condition is
  removed, a failed verdict becomes pass, missing evidence is supplied, or a
  blocker is removed under the selected Commitment, scope, and verifier
- **AND** the budget accounts for repeated failures, evidence quality, model tier,
  concurrency and coordination cost, elapsed time, and remaining proof cost
- **AND** moving behavior or output between carriers, multiplying agents, or
  repeating unchanged analysis, tests, commits, or mutation is not counted as gain
- **AND** the same normalized failure signature converges through warning,
  bounded retry, then `blocked` or `await-user` rather than speculative churn

#### Scenario: recovery or a dashboard needs execution context
- **WHEN** execution pauses, another host takes over, or a dashboard renders
- **THEN** only information not reconstructible from Git, OpenSpec, and current
  ETHOS facts may enter a minimal recovery checkpoint
- **AND** dashboards remain read-only projections and neither surface owns
  lifecycle state, tasks, archive, or completion
