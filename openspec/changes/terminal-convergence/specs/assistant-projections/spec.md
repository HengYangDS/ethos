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

#### Scenario: one lifecycle node requires several skills
- **WHEN** operation, subject, carrier role, changed paths, risk, and lifecycle
  facts require multiple capabilities at the same node
- **THEN** ETHOS compiles one ordered dependency-complete skill set rather than
  selecting a single winner or relying on prompt keyword matching
- **AND** required skills run before the earliest governed effect they protect,
  while advisory skills are demand-loaded and token-bounded
- **AND** a missing, stale, overlapping, or host-incompatible required projection
  blocks status, plan, or prewrite with one repair action

#### Scenario: an agent ignores projected instructions
- **WHEN** Codex, Claude, or another host edits files or invokes Git without
  following a generated Skill or slash command
- **THEN** repository-native prewrite, hook, exact-CAS, proof, and publication
  enforcement still reject the inadmissible transition
- **AND** host instructions improve left-shifted guidance but never constitute
  the security or authority boundary

#### Scenario: an ecosystem capability is installed
- **WHEN** a method pack, review lens, policy bundle, schema, plugin, agent-host
  projection, protocol adapter, forge adapter, or provider integration is added
- **THEN** it declares capability identity, contract and protocol versions,
  operations, required permissions, provenance, compatibility, conformance tests,
  demand-loading behavior, failure semantics, and uninstall effects
- **AND** discovery and release inventory derive from the same declaration rather
  than parallel manifests and code registries
- **AND** removing the extension leaves the kernel, repository truth, and native
  lifecycle complete

#### Scenario: an agent runtime or host is replaced
- **WHEN** a repository operation moves between models, agent SDKs, Codex,
  Claude, another harness, an IDE, or a remote agent
- **THEN** the same selected intent, actor and capability identity, permission
  boundary, TransitionPlan input, verdict schema, effect identity, and
  Attestation contract remain valid
- **AND** prompts, conversations, turns, sessions, traces, and private memory are
  not required to reconstruct authority or continue the repository lifecycle

#### Scenario: an agent protocol projects ETHOS
- **WHEN** MCP, A2A, ACP, or another admitted protocol exposes ETHOS capabilities
- **THEN** the adapter negotiates the protocol and maps its native discovery,
  request, progress, result, cancellation, and error forms onto the shared typed
  application service and conformance cases
- **AND** protocol Task, session, artifact, content, or extension state does not
  own OpenSpec tasks, Leases, TransitionPlans, effects, or repository truth
- **AND** removal of that adapter leaves CLI, SDK, subprocess JSON, and native
  repository enforcement complete

#### Scenario: agent execution is observed
- **WHEN** a host or runtime emits OpenTelemetry-compatible model, token, tool,
  handoff, latency, retry, or cost telemetry
- **THEN** ETHOS may use it for matched workflow evaluation and diagnostics
- **AND** missing, sampled, mutable, or vendor-hosted telemetry cannot authorize
  an effect, satisfy proof, or replace a HEAD-bound Attestation

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
