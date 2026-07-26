---
subject: ethos:evolution-intake-dispatch-kernel
role: plan
state: planned
relations:
  derives_from: product-design-contract, command-plane, expert-committee-review, external-framework-research
  governs: agentic issue intake, dispatch, evidence binding, and bounded repository evolution boundaries
---

# Agentic Evolution Kernel

Status: planned design substrate.

Purpose: define the terminal design for ETHOS to convert and govern external
signals, issue trackers, managed-agent platforms, and coding-agent runtimes
without turning any of them into repository truth.

This document is design truth candidate only. It does not implement intake
mining, issue creation, agent dispatch, or automatic mutation.

## Root Judgment

ETHOS must not become a clone of Multica, OpenHands Agent Canvas, GitHub
Copilot coding agent, Codex, GitLab Duo, OpenHands Resolver, SWE-agent, Beads,
Linear, Jira, GitHub Issues, or GitLab Issues.

Those tools are useful vessels. They can perceive, render, schedule, route, and
execute. ETHOS must remain the governed repository trust kernel: authority,
subject, commitment, change, evidence, claim, and chronicle.

The design center is therefore not "automatically find issues and assign agents".
The design center is:

```text
external disturbance -> bounded repository change -> proof-limited claim -> judged chronicle
```

In compact form:

```text
outer tools perceive and execute; ETHOS admits, proves, judges, and remembers.
```

This is a boundary-conversion design, not a tool-adoption design. Provider
signals enter as intake envelopes; ETHOS classifies, admits, proves, binds
claims, and records chronicle decisions. No provider surface may collapse those
conversions or become repository truth.

## Ontological Boundaries

The mechanism is valid only while these distinctions hold:

| Distinction | Meaning | Failure if collapsed |
| --- | --- | --- |
| Signal != Issue | A signal is a disturbance; an issue is an admitted problem candidate. | Noise becomes backlog sovereignty. |
| Issue != Change | An issue asks for attention; a change is authorized intervention. | Every observation becomes mutation pressure. |
| Agent output != Truth | Agent text, patches, logs, and PRs are candidate material. | Fluent narratives overwrite repository authority. |
| Execution != Proof | A task run is telemetry; proof is verifier-bound evidence. | Completed jobs masquerade as correctness. |
| Proof != Publication | Proof binds a HEAD and scope; publication makes an external commitment. | Local readiness is mistaken for shipped state. |
| Skill memory != Chronicle | Skills and memories help future runs; chronicle records judged repository history. | Private host memory becomes unreviewable truth. |
| Board state != Repository state | Boards, assignments, labels, and comments are projections. | Provider state becomes product lifecycle. |

ETHOS bounded repository evolution means better bounded conversion between
signals, changes, evidence, claims, and chronicle. It does not mean the
repository silently authorizes itself to rewrite its authority model.

## External Framework Lessons

### Managed-agent platforms

Multica's useful abstraction is not a new ontology. Its useful abstraction is
that agents can be treated operationally as teammates: assignable, visible,
commenting, blocking, and attached to reusable skills. ETHOS should absorb this
as an actor and invocation read model, not as a truth source.

Borrow:

- human and agent participants on one coordination surface;
- issue-to-agent lifecycle telemetry;
- runtime capability profiles;
- squad or routing groups as dispatch hints;
- recurring autopilots as intake triggers;
- skill compounding as candidate learning, only after promotion into tracked
  evidence, bounded claims, or judged chronicle.

Multica also exposes a useful split between issue state and execution-task
state: assigning an issue creates a queued task, a local daemon picks it up,
creates an isolated working directory, invokes the coding tool, reports
progress, and returns a success or failure result. ETHOS should borrow that
separation as telemetry: issue assignment may start work, but the execution task
is still not proof.

Do not borrow:

- board state as lifecycle truth;
- platform skills as repository truth;
- task completion as proof;
- agent assignment as authority;
- a vendor-specific lifecycle grammar.

### Automation canvases

OpenHands Agent Canvas and similar systems are good event, schedule, webhook,
and backend orchestration surfaces. ETHOS should delegate event loops and
runtime queues to them while owning admission policy and evidence binding.

Borrow schedules, webhook triggers, backend switching, automation health, and
side-effect logs. Do not borrow always-on automation as authority. A cron tick,
GitHub event, Slack command, or Linear update may create an intake envelope; it
must not directly mutate tracked repository truth.

### Hosted coding agents

GitHub Copilot coding agent, Codex, GitLab Duo, OpenHands Resolver, SWE-agent,
and similar tools can produce branches, patches, PRs, merge requests, comments,
or logs. ETHOS should treat each as an execution backend with an explicit
capability level.

Hosted agents are opaque by default. They should normally enter as patch
producers or remote-branch producers until they can prove root binding,
expected-head discipline, prewrite admission, and evidence capture.

Hosted issue-to-PR / issue-to-MR flows are especially useful as L3 remote branch
executors. Their native object is a provider branch plus review surface. ETHOS
should import that branch or patch into a Work Lane boundary, then prove it
through ETHOS gates. Provider review status, generated plans, and green hosted
checks are helpful evidence candidates, not final claims.

### Local-first task graphs

Beads-like task ledgers can be useful local-first issue graphs for agents and
humans. They remain task-ledger adapters. They do not own Change, Claim, or
Chronicle.

Borrow dependency-aware ready queues, stable hash ids, branch-friendly task
storage, JSON output, duplicate / supersession links, and compaction as a
context-management technique. Do not borrow a task graph as Chronicle. A task
ledger remembers what workers intended and did; Chronicle remembers what ETHOS
judged and promoted.

## Research Calibration

Research calibration as of this design review changes the implementation posture but not the root boundary:

| System | Strong mechanism | ETHOS interpretation |
| --- | --- | --- |
| Multica | Human / agent assignees, comments, mentions, squads, autopilots, task queue, local daemon execution. | Collaboration and runtime projection; useful for actor visibility and dispatch telemetry. |
| GitHub Copilot coding agent | Assign issue or prompt task; issue assignment creates a pull request; API supports target repo, base branch, instructions, custom agent, and model. | L3 remote branch executor; PR is candidate material until imported and proved. |
| OpenHands Agent Canvas / Resolver | Scheduled and event-driven automations; GitHub issue triggers via label or mention; local / remote / cloud backends. | Event and backend orchestration plane; ETHOS owns admission and evidence binding. |
| GitLab Duo Agent Platform | Developer Flow can create draft merge requests from issues, iterate on MR feedback, research, split MRs, and resolve conflicts. | L3 merge-request executor and research backend; MR state is projection. |
| SWE-agent family | Issue-to-patch / issue-to-repair runner optimized for benchmarkable repository tasks. | Patch producer or lane executor depending on root/head/evidence capability. |
| Beads | AI-oriented dependency graph, stable ids, ready queue, branch-friendly storage, JSON surfaces. | Optional local task-ledger adapter; not Change, Claim, or Chronicle. |
| Renovate / Dependabot | Dependency scanners that can open pull requests and sometimes dashboard issues. | Supply-chain signal and candidate-patch producers; PRs still require ETHOS proof and claim binding. |
| CodeQL / SonarQube / Semgrep | Static analysis, rule findings, code-scanning alerts, pull-request comments, and suggested fixes. | Sensor plane and evidence-candidate plane; findings are signals until admitted, deduped, and proved. |

The common pattern is clear: modern systems are converging on issue as trigger,
agent as assignee, branch or PR/MR as output, and comments as telemetry. ETHOS
must sit one layer deeper: signal as input, Work Lane as containment, proof as
truth boundary, claim as limited speech, chronicle as judged memory.

The second common pattern is equally important: mature non-agent systems already
perform large parts of the sensing loop. Dependency bots, static analyzers,
runtime monitors, CI checks, security scanners, and review bots can discover
invalid states faster than a general agent committee. ETHOS should not replace
those sensors. It should normalize their findings into intake envelopes,
deduplicate them as issue candidates, and admit only the bounded changes that
pass repository authority.

## Layer Ownership

| Layer | Examples | ETHOS ownership | Rule |
| --- | --- | --- | --- |
| Board / collaboration | Multica, GitHub Issues, GitLab Issues, Linear, Jira, Beads | Partial read model only | Render and request work; do not mint truth. |
| Event / automation | webhooks, schedules, autopilots, Agent Canvas, CI triggers | Admission policy only | Events may create intake records; not mutation rights. |
| Execution | Codex, Copilot, Duo, Claude Code, OpenHands, SWE-agent | No | Backends produce candidate material and evidence candidates. |
| Truth / evidence | Git, Work Lane, OpenSpec, source, tests, schemas, docs, evidence, claims, chronicle | Yes | Repository truth and lifecycle remain here. |

The thin waist is ETHOS command JSON and repository evidence, not any external
board or agent runtime.

## Terminal Organ Model

The terminal design is not a bigger agent. It is a governed organism whose
organs have different authorities:

| Organ | Function | May do | Must not do |
| --- | --- | --- | --- |
| Sensor | Perceive disturbances from reports, scanners, humans, boards, CI, runtime logs, dependency bots, and agents. | Emit signals and intake envelopes. | Decide truth, create commitments, or mutate source. |
| Normalizer | Convert heterogeneous signals into typed ETHOS envelopes. | Preserve provenance, subject hints, evidence hints, and risk hints. | Hide source uncertainty or collapse signals into issues. |
| Adjudicator | Dedupe, classify, prioritize, and decide whether a candidate deserves attention. | Produce issue candidates and recommended dispositions. | Treat issue existence as change authorization. |
| Admitter | Convert a candidate into a bounded change only when authority, scope, owner, proof route, and rollback are known. | Create or bind OpenSpec, claim, Work Lane, and proof expectations. | Let provider assignment, agent confidence, or board priority authorize mutation. |
| Executor | Perform bounded work through a human, local agent, hosted agent, or automation backend. | Produce patches, branches, result packages, logs, and evidence candidates. | Claim completion, publish, or rewrite authority. |
| Prover | Run repository gates with HEAD, scope, command, and artifact binding. | Admit evidence and constrain claims. | Substitute green provider status or agent narrative for proof. |
| Chronicler | Record judged memory, remaining risk, supersession, rejection, and learning. | Preserve decisions and trigger upstream guardrail proposals. | Store raw telemetry as truth or preserve every event as doctrine. |
| Upstreamer | Move repeated failures into rules, hooks, schemas, scaffolds, defaults, or skills. | Reduce future ambiguity and prevent recurrence. | Grant ETHOS new authority without the same admission and proof discipline. |

The organ model is the guard against both under-automation and over-automation.
It lets ETHOS use many powerful surfaces while keeping one governed kernel.

## Autonomy Invariants

ETHOS becomes more autonomous only when autonomy reduces ungoverned discretion.
The following invariants are stronger than any vendor integration:

1. Every autonomous step must narrow a type, not blur one: signal to envelope,
   envelope to candidate, candidate to admitted change, change to Work Lane,
   Work Lane to proof, proof to claim, claim to chronicle.
2. Every write-capable step must have a stop condition: expected head, owner,
   root, scope, forbidden paths, proof route, rollback, and publication
   boundary.
3. Every repeated failure must move upstream only after judgment: incident to
   diagnosis, diagnosis to hypothesis, hypothesis to change, change to proof,
   proof to rule / hook / schema / scaffold / default.
4. Every automation must retire more ambiguity than it creates. A bot that
   creates more untriaged cards, stale branches, or unverifiable claims than it
   resolves is negative autonomy.
5. ETHOS may not self-authorize authority expansion. Changes to authority
   order, release policy, protected roots, proof gates, external publication, or
   backend trust levels require maintainer-visible admission and evidence.

The Dao-aligned direction is therefore not maximum action. It is minimum
unproven action and maximum proven learning.

## Kernel Flow

The terminal flow is:

```text
signal
  -> intake envelope
  -> issue candidate
  -> admitted change
  -> Work Lane + claim
  -> agent invocation
  -> result package
  -> proof
  -> land / publication-readiness / authorized publish
  -> chronicle
  -> evolution decision
```

Mapped to the ETHOS kernel:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

Every arrow is a type conversion with explicit authority, scope, evidence, and
boundary. Nothing should slide automatically from one type to the next.

## Evolution Ladder

The design should mature by adding one irreversible type conversion at a time:

| Stage | New capability | Output | Forbidden shortcut |
| --- | --- | --- | --- |
| E0 | Observe repository and provider signals. | Intake envelopes. | Treat signal as issue. |
| E1 | Dedupe and classify invalid states. | Issue candidates. | Treat candidate as authorized change. |
| E2 | Project candidates to boards in dry-run or authorized apply mode. | External issue/card projection. | Treat external issue state as lifecycle truth. |
| E3 | Plan admitted work. | Dispatch envelope. | Dispatch without Work Lane, expected head, scope, proof, and rollback. |
| E4 | Invoke backend. | Backend run and result package. | Treat backend completion as proof. |
| E5 | Import and prove. | HEAD-bound evidence. | Let provider checks replace ETHOS gates. |
| E6 | Bind claim and chronicle. | Limited claim and judged memory. | Let private memory or task ledger replace chronicle. |
| E7 | Move repeated failures upstream. | Rule, hook, schema, scaffold, default, or skill. | Let automation rewrite authority or publish itself. |

Only E0 and E1 are safe as the first implementation slice. E2 may be automated
only after dry-run output has proven low noise and strong dedupe. E3 and above
must stay behind explicit admission until backend capability levels are proven.

## Intake Envelope

An intake envelope normalizes an external or internal disturbance. It is read
model input and never authorizes mutation.

Required fields:

| Field | Meaning |
| --- | --- |
| `source_provider` | `ethos`, `github`, `gitlab`, `multica`, `openhands`, `codex`, `beads`, or another adapter id. |
| `source_ref` | Stable external or internal reference. |
| `observed_at` | Observation timestamp. |
| `actor` | Human, bot, agent, service, or scheduled automation that supplied the signal. |
| `target_root` | Repository root the signal claims to concern. |
| `subject_hint` | Path, package, command, gate, rule, doc, or surface hinted by the signal. |
| `signal_type` | Failure, drift, advisory, request, review, vulnerability, dependency update, recurring audit, or human request. |
| `evidence_hint` | Command, artifact, provider URL, log digest, or observation reference. |
| `risk_hint` | Initial risk category before ETHOS triage. |
| `repository_truth` | Always false for external providers. |

## Issue Candidate

An issue candidate is a deduplicated, bounded problem candidate. It still does
not authorize mutation.

Required fields:

| Field | Meaning |
| --- | --- |
| `candidate_id` | Stable id derived from subject, invalid state, and evidence digest. |
| `subject` | Governed object. |
| `violated_commitment` | Contract, rule, spec, gate, or expectation implicated by the signal. |
| `invalid_state` | ETHOS invalid-state taxonomy id or `unclassified_invalid_state`. |
| `scope` | Paths, packages, commands, or docs affected. |
| `severity` | Blocking, advisory, hygiene, research, or opportunity. |
| `dedupe_key` | Hashable duplicate boundary. |
| `suggested_disposition` | Reject, observe, raise issue, require triage, propose change, or dispatch eligible. |
| `suggested_proof` | Proof route if it becomes a change. |
| `auto_raise_allowed` | Whether external issue creation may be automated. |
| `auto_dispatch_allowed` | Whether agent dispatch may be automated. |

## Dispatch Envelope

A dispatch envelope is the first object that may authorize an execution backend
to act, and only within declared limits.

Required fields:

| Field | Meaning |
| --- | --- |
| `change_id` | ETHOS change id or issue-derived change candidate id. |
| `claim_id` | Claim id when trust-bearing. |
| `owner` | Lane owner or delegated actor. |
| `target_root` | Absolute repository root. |
| `work_lane` | Owned `work/*` lane or remote branch mapped to one. |
| `expected_head` | HEAD at dispatch time. |
| `allowed_paths` | Tracked paths the backend may change. |
| `forbidden_paths` | Protected or out-of-scope paths. |
| `backend_profile` | Capability profile and trust level. |
| `required_gates` | Gates from `ethos plan` / policy. |
| `evidence_requirements` | Command, artifact, digest, and HEAD-binding expectations. |
| `rollback_plan` | Recovery branch, patch, or revert plan. |
| `publication_boundary` | Local proof, candidate land, accepted-root closeout, publication-readiness, authorized publication, or release boundary. |

No dispatch envelope may target the accepted root or candidate worktree for
normal edits.

## Backend Capability Levels

| Level | Name | Capability | Default use |
| --- | --- | --- | --- |
| L0 | Observe | Read and report only. | Research, triage, review. |
| L1 | Patch producer | Produces diff or recommendation; ETHOS applies separately. | Opaque hosted agents. |
| L2 | Lane executor | Mutates an admitted Work Lane with prewrite and evidence capture. | Trusted local agents. |
| L3 | Remote branch executor | Produces provider branch or PR/MR; ETHOS imports and proves. | Copilot, Codex cloud, Duo, OpenHands hosted. |
| L4 | Trusted runner | Executes ETHOS commands, preserves root/head binding, and emits evidence. | Mature controlled runners only. |

Higher levels are not moral trust. They are measured capability contracts.
Backends degrade to the lowest level they can prove.

## Automation Permission Levels

| Level | Action | Default policy |
| --- | --- | --- |
| A0 | Observe signals. | Allowed. |
| A1 | Suggest issue candidates. | Allowed. |
| A2 | Raise external issue or board card. | Dry-run by default; apply requires authorization. |
| A3 | Plan dispatch. | Allowed when Work Lane and proof route are known. |
| A4 | Assign agent backend. | Requires dispatch envelope. |
| A5 | Execute in lane or remote branch. | Requires backend capability admission. |
| A6 | Land. | ETHOS lifecycle only, never board/backend authority. |
| A7 | Publish. | Separate human or release authorization. |

Governance semantics, authority order, hooks, release policy, evidence policy,
and product-boundary changes should not auto-dispatch without maintainer review.

## Execution Contract

Before execution, ETHOS must have:

- status and root binding;
- owned Work Lane or import branch boundary;
- claim binding when trust-bearing;
- OpenSpec carrier for non-trivial governance/product changes;
- path scope and forbidden paths;
- expected head;
- proof plan;
- rollback plan.

During execution, the backend must preserve:

- prewrite before tracked mutation;
- expected-head checks at major transitions;
- scope fuse on unexpected paths;
- command, cwd, head, exit code, artifact, and digest capture;
- stop-on-conflict behavior;
- provider side-effect log.

After execution, ETHOS imports a result package and judges it through proof,
claim, chronicle, and lane lifecycle. Backend completion status is not an ETHOS
completion state.

## Result Package

A backend result package records:

- backend id and run id;
- actor and owner;
- start head and final head;
- changed paths;
- commits, patch digest, PR/MR reference, or artifact references;
- dirty-state report;
- commands and exit codes when available;
- deviations from dispatch envelope;
- provider side effects;
- rollback notes.

The package is an evidence candidate. It becomes durable evidence only after
promotion into tracked evidence or another configured durable evidence root.

## Proof, Claim, and Chronicle

Proof must be HEAD-bound, command-bound, and scope-bound. If HEAD moves during a
proof bundle, the evidence is stale and must be rerun.

A claim says only what evidence proves. It must not expand an agent's summary
into semantic truth.

Chronicle is judged memory. It records decisions, supersession, evidence used,
current-truth impact, remaining risk, and whether a repeated failure should move
upstream. It is not a raw event stream, chat transcript, or board history.

## Bounded Repository Evolution Rule

Repeated late failures do not trigger autonomous evolution. They may become
upstream constraints only through the governed path:

```text
incident -> diagnosis -> hypothesis -> OpenSpec/change -> Work Lane -> proof -> claim -> chronicle -> rule/hook/scaffold/schema/default
```

ETHOS may observe repository state, diagnose repository state, suggest bounded
changes, and prove bounded changes within bounded lanes. It must not authorize
itself, certify itself, or publish itself outside configured authority.

## Failure Modes and Guardrails

| Failure mode | Guardrail |
| --- | --- |
| Adapter sovereignty inversion | External tools remain adapters/projections; promotion requires ETHOS evidence, claim, and chronicle. |
| Noise backlog sovereignty | Signals pass through dedupe, invalid-state classification, severity, and disposition before issue creation. |
| Issue-to-mutation collapse | Issues do not authorize changes; dispatch requires Work Lane, scope, proof, and rollback. |
| Agent narrative truth | Agent output is candidate material; repository truth remains source, tests, docs, OpenSpec, evidence, claims, Git facts. |
| Evidence inflation | Claims must name verifier, command, scope, HEAD, artifact, and digest. |
| Last-writer-wins | One Work Lane per change, lease/actor match, expected-head checks, path-scope overlap checks, proof after replay. |
| Hidden learning loop | Skills and memories become evolution only after tracked promotion and evidence. |
| Chronicle poisoning | Chronicle records judged decisions, not raw telemetry. |
| Publication confusion | Land, accepted-root closeout, hosted CI, remote publication, and release remain separate states. |

## First Implementation Slice

The first implementation slice is now read-only intake mining.

Current command:

```bash
ETHOS_ACTOR=codex uv run ethos intake mine --json
```

As of the current implementation, this command reads repository claim evidence
signals and projects them into intake envelopes and issue candidates without
mutating the repository. Its output is explicitly bounded:

- `repository_truth=false`;
- `writes=[]`;
- `truth_boundary=repository-readmodel`;
- `auto_raise_allowed=false` in the summary;
- `auto_dispatch_allowed=false` in the summary.

This makes `intake mine` an E0/E1 read model: it senses and classifies; it does
not raise external issues, admit changes, create Work Lanes, assign agents,
prove, land, publish, or chronicle by itself.

Current and future sources:

```bash
ETHOS_ACTOR=codex uv run ethos status --root <target-root> --json
ETHOS_ACTOR=codex uv run ethos prove --gate evidence-freshness --root <target-root> --json
ETHOS_ACTOR=codex uv run ethos prove --gate claims --root <target-root> --json
ETHOS_ACTOR=codex uv run ethos lane status --root <target-root> --json
ETHOS_ACTOR=codex uv run ethos campaign hypotheses --root <target-root> --json
```

The current machine output lives in command JSON under `intake_envelopes` and
`issue_candidates`. Future adapters may also write generated evidence-candidate
artifacts, but those artifacts should not be committed as truth unless they are
summarized into durable evidence or used by a promoted claim.

Minimum candidate quality:

- every candidate has a source command, source artifact, subject, invalid-state
  taxonomy id or `unclassified_invalid_state`, severity, dedupe key, and
  suggested proof route;
- every candidate distinguishes blocking defects from advisory opportunities;
- repeated candidates collapse under the same dedupe key unless the invalid
  state or evidence digest changes;
- no candidate carries mutation authority;
- no output claims more than the source command proves.

The next safe slice is not automatic dispatch. It is issue projection dry run:
`ethos intake raise --dry-run --json`. Its job is to show what would be raised
to GitHub, GitLab, Multica, Beads, or another board without creating provider
truth. It must preserve `Issue != Change` and keep
`auto_dispatch_allowed=false`.

## Later Slices

1. `intake raise --dry-run --json`, followed later by explicitly authorized
   apply adapters for GitHub, GitLab, Multica, Beads, or other board
   projections.
2. `dispatch plan` to produce a dispatch envelope from an admitted change.
3. `dispatch assign --dry-run --json`, followed later by authorized apply
   adapters to project assignments into Codex, Copilot, GitLab Duo, OpenHands,
   or another backend.
4. Result-package import and proof binding.
5. Chronicle-backed evolution decisions.
6. Upstream guardrail proposal and promotion: rule, hook, schema, scaffold,
   default, or skill.

Each slice must keep the command plane small. New commands must reduce invalid
states, not create a parallel lifecycle.

## Research Sources

Research calibration used during this design review:

- [Multica Issues](https://www.multica.ai/docs/issues)
- [Multica Agents](https://www.multica.ai/docs/agents)
- [Multica Assigning Issues](https://www.multica.ai/docs/assigning-issues)
- [GitHub Copilot coding agent task kickoff](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/kick-off-a-task)
- [GitHub Copilot cloud agent API](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api)
- [OpenHands Agent Canvas overview](https://docs.openhands.dev/openhands/usage/agent-canvas/overview)
- [OpenHands GitHub Action](https://docs.openhands.dev/openhands/usage/run-openhands/github-action)
- [GitLab Duo Agent Platform Developer Flow](https://docs.gitlab.com/user/duo_agent_platform/flows/foundational_flows/developer/)
- [Beads documentation](https://gastownhall.github.io/beads/)
- [SWE-agent repository](https://github.com/SWE-agent/SWE-agent)
- [Renovate pull requests](https://docs.renovatebot.com/key-concepts/pull-requests/)
- [Renovate how it works](https://docs.renovatebot.com/key-concepts/how-renovate-works/)
- [Dependabot pull requests](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-pull-requests)
- [CodeQL code scanning](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-code-scanning)
- [SonarQube issues](https://docs.sonarsource.com/sonarqube-server/user-guide/issues/introduction)
- [Semgrep AppSec Platform findings dedupe](https://semgrep.dev/docs/kb/semgrep-appsec-platform/findings-count-differ-api-platform)

## Terminal Formula

```text
外器感之，内核裁之；
Work Lane 行之，证据限之；
Claim 言之，Chronicle 藏之；
可证则进，不证则止；
屡败上移，固化为 rule / hook / scaffold / schema / default。
```

Engineering form:

```text
Perception is external.
Judgment is ETHOS.
Execution is delegated.
Truth is repository-bound.
Learning is chronicle-bound.
Evolution is admitted, proved, and retired.
```

This is the intended terminal posture: many obedient surfaces, one governed
truth kernel.
