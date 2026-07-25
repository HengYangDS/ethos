---
subject: ethos:lane-lease-governance-research
role: research
state: experimental
relations: supports: lane lease governance design, net-gain destructive change governance, multi-agent work lane coordination
updated: 2026-07-06
---

# Lane Lease Governance Research Intake

## Decision context

ETHOS has multiple Codex and Claude agents working in the same repository. The
failure mode is not merely branch clutter; it is that Git refs and worktrees do
not encode who owns an action, which paths are in scope, whether the holder is
fresh, whether another agent may only observe, and when a destructive change is
allowed because it has net gain.

The design goal is therefore not conservative lock-down. ETHOS should permit
creative, architectural, and destructive changes when they are bounded,
observable, reversible, and evidence-positive. Governance should prevent
unauthorized intrusion into another Work Lane while making owned lanes powerful
enough to break obsolete structure deliberately.

## Source rules

This intake prioritizes official or primary sources. External systems are used
for mechanism extraction, not runtime adoption by default. A mechanism is
accepted only if it maps cleanly to existing ETHOS primitives: Work Lane,
lease, claim, scope, status, proof, evidence, candidate train, and accepted-root
closeout.

## Findings by mature mechanism

### Kubernetes Lease

Kubernetes models coordination through Lease objects in the
`coordination.k8s.io` API group. The docs describe Leases as a lightweight
coordination mechanism used for node heartbeats and leader election. The useful
ETHOS lesson is the tuple of `holder`, freshness time, and renewal: ownership is
not a timeless fact; it must be refreshed and observable.

ETHOS adaptation:

- Use a local lane lease with `holder`, `heartbeat` / `renewed_at`, and expiry.
- Treat stale lease as `handoff_required`, not as permission to delete.
- Do not introduce Kubernetes or an API server.

Primary source: <https://kubernetes.io/docs/concepts/architecture/leases/>

### etcd lease / concurrency

etcd exposes lease-backed coordination and higher-level concurrency primitives
such as locks and elections. The durable idea is that lease expiry can revoke a
holder's right, while monotonically ordered revisions can serve as fencing.

ETHOS adaptation:

- Add an `epoch` to each lane lease and require write / closeout gates to check
  the current epoch.
- On adoption or ownership transfer, increment epoch so an old resumed agent is
  fenced out.
- Do not introduce etcd for local repository coordination unless multi-host
  distributed execution becomes a real requirement.

Primary source: <https://etcd.io/docs/>

### ZooKeeper ephemeral sequential locks

ZooKeeper recipes use ephemeral sequential znodes for locks. The smallest
sequence owns the lock, ephemeral nodes disappear when sessions expire, and
watching the predecessor avoids a thundering herd. The useful principle is not
ZooKeeper itself, but session-tied ownership plus ordered succession.

ETHOS adaptation:

- Lease state should be session-like and expire separately from Git branch
  existence.
- Adoption should be explicit and ordered, not a race among agents.
- Do not introduce ZooKeeper or a central lock service for a local Git common-dir
  problem.

Primary source: <https://zookeeper.apache.org/doc/current/recipes.html>

### Redis Redlock and distributed lock cautions

Redis documents Redlock as an algorithm for distributed locks, but the broader
literature around distributed locks warns that lease expiry without fencing can
allow an old holder to resume and write after another holder has acquired the
lock. The useful lesson is negative: TTL alone is not enough for correctness
when writes have durable effects.

ETHOS adaptation:

- Lease expiry alone must not authorize mutation.
- Every mutation-sensitive command needs a fresh epoch / fencing check.
- Prefer Git common-dir local leases plus reference-transaction hooks over a
  Redis runtime.

Primary source: <https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/>

### Git reference-transaction hook

Git's `reference-transaction` hook can observe prepared / committed / aborted
reference updates and can reject prepared updates. This is the substrate-level
place to block direct movement or deletion of protected refs.

ETHOS adaptation:

- Protect `refs/heads/work/*`, `refs/heads/candidate/*`, and accepted roots from
  raw ref movement.
- Permit only sanctioned ETHOS commands carrying expected head, authorization,
  and lease / epoch context.
- Keep this as the final guardrail; user-facing UX should fail earlier via
  status, prewrite, and closeout gates.

Primary source: <https://git-scm.com/docs/githooks>

### GitHub / GitLab / Gerrit ownership and proposal gates

Hosted code collaboration systems converge on three ideas: code ownership,
protected refs, and proposal / merge gates. GitHub CODEOWNERS and branch
protection/rulesets, GitLab Code Owners and approvals, and Gerrit proposal
requirements all separate authorship from authority to integrate.

ETHOS adaptation:

- Map code ownership to lane scope and claim ownership, not to hosted PRs as the
  local truth source.
- Treat closeout as a proposal gate: owner / proof / candidate / overlap checks
  must pass before integration.
- Hosted PR/MR systems are publication surfaces, not the local source of truth
  for Work Lane lifecycle.

Primary sources:

- <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners>
- <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>
- <https://docs.gitlab.com/user/project/codeowners/>
- <https://gerrit-review.googlesource.com/Documentation/config-proposal-requirements.html>

### OpenTelemetry

OpenTelemetry standardizes telemetry signals such as traces, metrics, and logs.
The useful idea is signal separation: traces explain a workflow path, metrics
summarize health, and logs preserve discrete events.

ETHOS adaptation:

- Lane event log is the local trace of a Work Lane lifecycle.
- Coordination metrics should be few and discriminating: active lanes, stale
  leases, unknown scopes, overlaps, blocked closeouts, unauthorized attempts.
- Do not introduce a collector before `ethos status --json` and lane logs are
  correct.

Primary source: <https://opentelemetry.io/docs/concepts/signals/>

### CloudEvents and CDEvents

CloudEvents provides a common event envelope; CDEvents defines event semantics
for continuous delivery. These standards are useful because ETHOS needs events
that are readable by humans, agents, and future tools without inventing a
bespoke envelope.

ETHOS adaptation:

- Use a CloudEvents-like envelope for lane log entries: id, source, type,
  subject, time, data.
- Borrow CDEvents vocabulary where it fits delivery lifecycle events, but keep
  ETHOS lane semantics primary.
- Events remain projections of lane truth, not a second truth store.

Primary sources:

- <https://cloudevents.io/>
- <https://cdevents.dev/>

### SLSA, in-toto, Sigstore, and OpenSSF Scorecard

Supply-chain frameworks emphasize provenance, attestations, signed evidence,
and scored security posture. ETHOS does not need to become a supply-chain
platform, but its proof and closeout model should preserve subject, materials,
commands, environment, and result.

ETHOS adaptation:

- Use SLSA / in-toto style provenance for destructive changes and closeout:
  subject head, materials, commands, gates, actor, and result.
- Consider Sigstore / cosign only when publishing artifacts or external release
  integrity becomes in scope.
- Use OpenSSF Scorecard as inspiration for repo health checks, not as a hard
  dependency for local lane governance.

Primary sources:

- <https://slsa.dev/spec/v1.1/about>
- <https://in-toto.io/>
- <https://docs.sigstore.dev/>
- <https://quality_summary.dev/>

### OpenFeature and feature-flag discipline

OpenFeature provides a vendor-neutral feature flag API and specification. The
important architectural principle is decoupling deployment from activation.

ETHOS adaptation:

- Architectural or destructive migrations should prefer flags, shadow paths,
  compatibility modes, or branch-by-abstraction when a hard cutover would
  increase risk.
- Do not add a feature-flag SDK until runtime behavior genuinely needs it.
- Capture flag or shadow-mode evidence in the destructive-change record.

Primary source: <https://openfeature.dev/specification/>

### ADR, RFC, SRE error budgets, DORA, and chaos engineering

Mature change systems do not forbid large changes; they require rationale,
review, bounded blast radius, rollback, and measurable outcomes. ADR and RFC
capture why and what is being changed. SRE error budgets and canarying regulate
risk. DORA metrics turn net gain into measurable software delivery outcomes.
Chaos engineering adds hypothesis, steady state, blast radius, and stop
conditions.

ETHOS adaptation:

- Classify changes as routine, material, or architectural/destructive.
- Require ADR for material changes and RFC + rollback + experiment boundary for
  architectural/destructive changes.
- Require destructive changes to state intended net gain, evidence metric,
  abort condition, and rollback path.
- A failed bounded experiment can be a valid outcome if evidence is archived.

Primary sources:

- <https://adr.github.io/>
- <https://rust-lang.github.io/rfcs/>
- <https://sre.google/workbook/error-budget-policy/>
- <https://dora.dev/guides/dora-metrics/>
- <https://principlesofchaos.org/>

### Agent and tool protocols: MCP, A2A, OpenAI Agents SDK, Claude Code

Agent ecosystems are moving toward explicit tools/resources, handoffs,
structured events, guardrails, and tracing. These are useful as projections and
integration surfaces, not as replacement truth for the repository.

ETHOS adaptation:

- Keep repo truth in source, rules, schemas, lane leases, proof, and evidence.
- Expose ETHOS state through agent-friendly JSON and possibly MCP resources
  later.
- Do not rely on chat memory or vendor-specific subagent state for lane
  ownership.

Primary sources:

- <https://modelcontextprotocol.io/>
- <https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/>
- <https://openai.github.io/openai-agents-python/>
- <https://docs.anthropic.com/en/docs/claude-code>

## Accepted design implications

1. Lane is the governed resource; agent is only the temporary holder.
2. Lease without epoch is insufficient; stale holders must be fenced.
3. Scope is required for parallelism. Unknown overlap should block integration,
   not observation.
4. Foreign lanes are observable but not mutable.
5. Destructive change is allowed only with claim, hypothesis, blast radius,
   rollback, net-gain evidence, and archive.
6. Status and gate errors must prescribe legal next actions for agents.
7. External standards should inform envelopes and evidence shape, not introduce
   heavy runtimes before the local command plane needs them.
8. Governance must not collapse all gates into one coarse `blocked` state.
   Work Lane authoring, candidate integration, and accepted-root closeout have
   different proof burdens.

## Recommended adoption matrix

| Mechanism | Decision | ETHOS form |
| --- | --- | --- |
| Kubernetes Lease | Borrow | holder + heartbeat + expiry |
| etcd revision / fencing | Borrow | lease epoch |
| ZooKeeper sequential session | Borrow | ordered explicit adoption |
| Redis Redlock | Do not adopt | cautionary TTL-only anti-pattern |
| Git reference-transaction | Adopt | protected ref gate |
| GitHub/GitLab/Gerrit ownership gates | Borrow | owner-only closeout and protected proposal |
| OpenTelemetry | Borrow | trace/log/metric signal model |
| CloudEvents | Likely adopt lightly | lane event envelope |
| CDEvents | Borrow selectively | delivery lifecycle event vocabulary |
| SLSA / in-toto | Borrow | proof / closeout provenance shape |
| Sigstore | Defer | release artifact signing only |
| OpenFeature | Borrow | flags / shadow / gradual activation |
| ADR / RFC | Adopt | material/destructive change records |
| SRE / DORA / chaos | Borrow | net-gain metrics and experiment guardrails |
| MCP / A2A | Defer as projection | expose repo truth, not replace it |

## Immediate local findings

During this intake, `ethos lane start` failed when the host shell could resolve
`git` interactively but the CLI subprocess could not find bare `git`. The same
host also failed to resolve bare `env` in one command script while absolute
paths worked. This is an agent-friendliness finding: ETHOS commands should avoid
hidden dependence on fragile host PATH lookup where possible, or report a clear
remedy when a required tool is missing.

A second finding: running `ethos lane status` from a linked worktree still
reported the accepted root unless `--root` / `--editor-root` were provided in
later commands. This reinforces the UX principle that agent-facing commands
must make target root and editor root explicit and visible.

## Next probes

1. Inspect the current `work/lane-collaboration-readmodel` result before
   implementing overlapping coordination surfaces.
2. Decide whether lane log events should be strict CloudEvents or a compatible
   ETHOS profile.
3. Decide whether destructive-change governance belongs in a new schema or an
   extension of existing claim / evidence schemas.
4. Harden command UX around PATH, root, editor-root, and next-command remedies.

## Expert committee review, round 1

### Distributed systems chair

The core distributed-systems lesson is that a lease is not a lock unless it is
paired with fencing. Heartbeats make liveness observable; epoch or revision
makes stale holders harmless. ETHOS should therefore never treat `expires_at`
as sufficient authority. The gate must check the current lane epoch at write and
closeout time.

Decision: adopt lease + epoch locally; reject runtime ZooKeeper / etcd / Redis
until coordination spans multiple machines and cannot be represented by Git
common-dir state.

### Code collaboration chair

Hosted collaboration systems separate authorship, ownership, and integration.
ETHOS should mirror that split locally: an agent may author in its owned lane,
but integration into candidate / accepted root is a proposal-like action requiring
proof, scope checks, and owner authority. CODEOWNERS-style ownership should
inform scope and review, but hosted PR/MR state must not become the local source
of truth.

Decision: borrow owner-only closeout, protected refs, proposal queue semantics;
keep local Work Lane lifecycle as authority.

### Observability chair

The observable surface must be the lane lifecycle, not the chat. Status should
show role, authority, conflicts, and next legal action. Lane logs should be event
records. Metrics must remain few and tied to decisions: stale leases, unknown
scopes, overlaps, blocked closeouts, unauthorized attempts.

Decision: adopt an ETHOS profile of CloudEvents for lane events; borrow OTel's
signals taxonomy; defer collectors and dashboards.

### Supply-chain / proof chair

SLSA and in-toto show how to record what was built, from what materials, under
which process, and with what result. ETHOS closeout and destructive changes need
that same shape, but at repository-change scale rather than artifact-release
scale.

Decision: borrow provenance fields into proof / evidence; defer signing unless
release publication or external consumers require it.

### Creative-destruction chair

Governance must not freeze bad structure. The point of lane ownership is to let
the owner safely carry responsibility for bold change. Architectural or
destructive changes should require intent, hypothesis, blast radius, rollback,
net-gain metric, abort condition, and archived evidence. A bounded failed
experiment is acceptable if it increases knowledge and does not leak damage.

Decision: add a net-gain destructive-change policy; adopt ADR/RFC records only
for material and destructive changes, not routine edits.

## Standard and framework introduction decisions

| Candidate | Introduce as dependency? | Introduce as profile / schema? | Decision rationale |
| --- | ---: | ---: | --- |
| Kubernetes Lease | No | Yes, conceptually | Its holder + renew time model fits lane lease, but API server is unnecessary. |
| etcd concurrency | No | Yes, conceptually | Epoch/fencing is required; distributed KV is not. |
| ZooKeeper locks | No | No | Useful session ordering pattern, but too heavy and not aligned with local Git common-dir. |
| Redis Redlock | No | No | TTL-only locking is a cautionary anti-pattern without fencing. |
| Git reference-transaction | Existing substrate | Yes | Best low-level guard for protected refs. |
| GitHub/GitLab/Gerrit | No | Yes | Useful proposal and ownership semantics; hosted systems remain publication surfaces. |
| OpenTelemetry | No | Partial vocabulary | Signals taxonomy is useful; collector is premature. |
| CloudEvents | No runtime | Yes | Good envelope for lane log events. |
| CDEvents | No | Selective vocabulary | Useful for delivery lifecycle names; ETHOS lane semantics remain primary. |
| SLSA | No runtime | Provenance shape | Good for subject/material/process/result evidence. |
| in-toto | No runtime | Provenance shape | Useful evidence model; full layout/signing is premature. |
| Sigstore/cosign | Defer | Defer | Relevant to external artifact signing, not first local lane governance. |
| OpenFeature | No SDK yet | Conceptual | Flags/shadow/dual-run are key for destructive migration; SDK only when runtime flags exist. |
| ADR | Template | Yes | Adopt for material changes. |
| RFC | Template | Yes | Adopt for destructive or architectural changes. |
| SRE error budget | No | Conceptual | Use as change-risk budget when reliability evidence exists. |
| DORA metrics | No | Conceptual | Use for net-gain framing; do not force all repo work into service-delivery metrics. |
| Chaos engineering | No | Experiment guardrails | Hypothesis, steady state, blast radius, stop condition. |
| MCP/A2A | No | Projection later | Useful external interface; not a lane truth source. |

## Revised ETHOS design thesis

The mature-framework synthesis changes the thesis from defensive coordination to
bounded generative change:

> A Work Lane is a leased vessel for intentional repository mutation. It should
> protect other lanes from intrusion, but within its declared scope it should
> enable bold change when the claim states a net-gain hypothesis and the system
> can observe, fence, prove, roll back, and archive the result.

This implies two complementary policies:

1. **Foreign-lane restraint:** an agent may observe a foreign lane but must not
   write, rebase, close out, retire, or delete it without ownership transfer or
   maintainer adoption.
2. **Owned-lane potency:** an owner may perform destructive or architectural
   change when the change class requires and supplies intent, hypothesis, blast
   radius, rollback, abort condition, net-gain metric, and evidence.

## Proposed ETHOS primitives after research

Do not add a separate agent registry or mailbox unless these primitives prove
insufficient.

| Primitive | Role | Minimal carrier |
| --- | --- | --- |
| Work Lane | Governed mutation vessel | `work/*` branch + linked worktree |
| Lane Lease | Temporary right to act | Git common-dir runtime JSON |
| Epoch | Fencing token | lease field incremented on adoption/transfer |
| Scope | Parallelism and blast-radius boundary | claim / lease path list |
| Lane Event | Coordination and observability record | CloudEvents-like append-only log |
| Claim | Why the lane exists | existing claim evidence |
| Change Class | Routine/material/destructive classification | claim/evidence extension |
| Net-Gain Evidence | Proof that destructive change improved the system | evidence record / proof package |

## Implementation implications for the next stage

1. Before implementing new coordination code, inspect and absorb the existing
   `work/lane-collaboration-readmodel` lane if it lands. It appears to already
   touch coordination read models, invalid states, workspace-status schema, and
   lane tests. Duplicating that work would violate the foreign-lane rule.
2. First implement or refine observable read models before hard enforcement.
   Agents must see role, holder, scope, allowed actions, denied actions, and
   next commands.
3. Add epoch/fencing to lease semantics before relying on stale/adoption flows.
4. Add destructive-change classification after the lane lease gate exists,
   because net-gain permission depends on ownership and scope.
5. Add CloudEvents-like lane logs only as a profile over lane lease state, not as
   a second truth store.

## Non-goals

- No Kubernetes, ZooKeeper, etcd, Redis, or external lock service for local-only
  repo coordination.
- No hosted PR/MR system as local Work Lane truth.
- No general agent-to-agent chat system.
- No dashboard before command JSON is correct.
- No blanket ADR/RFC requirement for routine changes.
- No conservative ban on destructive change.

## Design intake for implementation

This research intake should drive implementation in four layers. The order is
intentional: make state visible before making enforcement stricter, then permit
higher-risk change only after ownership and evidence are reliable.

### Stage model: many lanes, one train, one history

The corrected concurrency model is not serial proof before all work. It is:

1. **Work Lane stage:** lanes may branch, explore, destroy, rebuild, and prove
   locally inside declared scope. Foreign parity or baseline debt should not
   prevent unrelated authoring.
2. **Candidate stage:** lanes are absorbed, compared, fused, and judged
   together. This is where overlap, baseline parity, and cross-lane proof debt
   become integration gates.
3. **Accepted-root stage:** the candidate train becomes durable history only
   after head-bound proof and sanctioned closeout.

The status surface should therefore classify authority as separate booleans,
not as a single `blocked` verdict:

```json
{
  "authoring_allowed": true,
  "integration_allowed": false,
  "accepted_closeout_allowed": false,
  "blocker": "baseline_parity_gapped",
  "blocker_owner": "work/parity-self-evidence-head",
  "allowed_next_actions": [
    "continue lane-local design",
    "run focused tests",
    "prepare integration notes"
  ]
}
```

In compact form: many Work Lanes may generate; candidate/dev selects and
integrates; accepted root records what has become law. 多 lane 并生，
candidate 取势，accepted 成法。

### Layer 1: discoverability before enforcement

Implement or refine read models before adding new hard blocks. A correct status
surface should answer four questions for both humans and agents:

1. What lane or root am I in?
2. What authority do I currently have?
3. Which foreign lanes, stale leases, unknown scopes, or overlaps affect me?
4. What is the next legal command?

The deeper requirement is discoverability: the system must make the legal path
visible at the moment of intent, not after a failed mutation. A human should be
able to glance at the command output and understand the situation. An agent
should be able to parse the same truth without reading prose or inferring from
Git internals.

The minimum useful output is not a dashboard; it is stable JSON plus a concise
human rendering. If the JSON is correct, IDE badges, MCP resources, terminal
prompts, and dashboards can remain projections. Projection may improve UX and
DX, but must not become lifecycle truth.

Required UX/DX properties:

- **Progressive disclosure:** default output shows role, stage gates, blockers,
  and next command; `--json` exposes full machine-readable detail.
- **Stage-aware next actions:** failures say whether authoring, candidate
  integration, or accepted closeout is blocked.
- **Copy-pasteable remedies:** every blocked state should include the exact next
  ETHOS command when one exists.
- **Agent affordances:** JSON fields use stable names, bounded enums, absolute
  roots, relative changed paths, and explicit capabilities.
- **Human affordances:** concise language distinguishes observe-only, write,
  land, adopt, retire, and closeout without requiring internal terminology.
- **DX locality:** command help, error text, and status output converge on the
  same nouns so contributors do not need to memorize hidden workflow rules.

### Layer 2: lease and fencing

Extend local lease semantics so every mutation-capable Work Lane has holder,
heartbeat, scope, and epoch. The epoch is the fencing token. Any command that
can write, land, retire, adopt, or move protected refs must compare the supplied
or resolved epoch with the current lease epoch. Adoption increments epoch.

This should first be enforced in ETHOS commands. Git hooks remain the fallback
substrate guard for raw ref operations.

### Layer 3: lane log and event profile

Use a CloudEvents-compatible ETHOS lane event profile, not a separate mailbox.
The event subject is the lane. The actor is the holder or maintainer. Event
types should be sparse and lifecycle-oriented:

- `lane.created`
- `lane.heartbeat`
- `lane.scope.declared`
- `lane.note.added`
- `lane.handoff.requested`
- `lane.adopted`
- `lane.proof.executed`
- `lane.land.requested`
- `lane.landed`
- `lane.retired`
- `lane.blocked`

This gives Codex, Claude, humans, and future tools a shared coordination trail
without introducing agent-to-agent chat as a truth source.

### Layer 4: net-gain destructive change

After lane ownership is enforceable, add change classification:

- `routine`: normal local proof is enough.
- `material`: requires ADR-style rationale.
- `destructive`: requires RFC-style proposal, net-gain hypothesis, blast radius,
  rollback, abort condition, and evidence archive.

A destructive change should be allowed to delete, replace, or reshape old
structures inside its declared scope. The system should not reject it because it
is disruptive; it should reject it only if the disruption is unbounded,
unowned, unobservable, unprovable, or irreversible.

## Minimal implementation slices

### Slice A: discoverable status and UX/DX read model

Goal: make current authority and next legal action visible before mutation.

Candidate changes:

- extend `ethos lane status --json` with `actor_role`, `allowed_actions`,
  `forbidden_actions`, `next_commands`, `authoring_allowed`,
  `integration_allowed`, and `accepted_closeout_allowed`;
- add a concise human rendering that names the current lane/root, capability,
  stage blockers, foreign lanes, and one recommended next command;
- ensure root/editor-root ambiguity is explicit and shown with absolute paths;
- make foreign lanes show observe-only authority and disjoint/overlap status;
- align `--help`, blocked-state messages, and JSON field names around the same
  vocabulary;
- keep all output derived from current repo state and lease state.

Acceptance evidence:

- unit tests for accepted root, owned lane, foreign lane, stale lease, and
  protected root;
- golden JSON checks for next commands and stage gates;
- CLI snapshot or contract tests for the human rendering;
- no new runtime dependency.

### Slice B: lease epoch and adoption

Goal: prevent stale holders from mutating after adoption.

Candidate changes:

- add `epoch` to local lane lease;
- make adoption increment epoch;
- make prewrite and closeout compare current epoch;
- add invalid states `lease_epoch_stale`, `lease_holder_mismatch`, and
  `stale_lane_without_adoption` if not already present.

Acceptance evidence:

- old holder fails prewrite after adoption;
- new holder succeeds after epoch bump;
- stale heartbeat alone does not permit deletion.

### Slice C: lane event profile

Goal: make coordination visible without adding a mailbox entity.

Candidate changes:

- append lane events under Git common-dir runtime state;
- use CloudEvents-compatible fields: `id`, `source`, `type`, `subject`, `time`,
  `data`;
- expose `ethos lane events <lane> --json` or include recent event summaries in
  lane status only if command surface remains small.

Acceptance evidence:

- lane start writes `lane.created`;
- heartbeat writes or updates heartbeat without noisy event spam;
- handoff/adoption/blocked events are visible;
- events never outrank lease state or proof.

### Slice D: destructive change admission

Goal: encourage creative destruction with net-gain discipline.

Candidate changes:

- extend claim/evidence or add a small destructive-change record schema;
- add ADR/RFC templates only for material/destructive classes;
- add checks for hypothesis, blast radius, rollback, abort condition, and
  evidence target;
- connect destructive class to scope and lane lease.

Acceptance evidence:

- routine change not forced through ADR/RFC;
- destructive change missing rollback or blast radius is blocked;
- destructive change with full record is admitted inside owned lane;
- failed bounded experiment can be archived without being treated as silent
  success.

### Slice E: protected ref fallback

Goal: prevent raw Git bypass of work/candidate/accepted refs.

Candidate changes:

- harden `reference-transaction` checks for work lanes, candidate, and accepted
  root;
- allow sanctioned ETHOS operations with expected head and authorization;
- fail closed when the command context cannot be proven.

Acceptance evidence:

- raw delete/move of active work lane is rejected;
- official retire-landed is accepted;
- raw accepted-root move is rejected;
- official closeout remains possible.

## Sequencing rule

Do not implement Slice D before Slice A and Slice B. Net-gain destructive change
requires clear ownership and visible authority. Otherwise the policy would
encourage powerful mutation before the system can tell who is responsible.

Do not implement dashboard or IDE projection before Slice A. Projection without
correct command JSON would create a second truth store.

Do not harden ref hooks before command-level remedies are clear. Hooks should be
the last guardrail, not the first user experience.

## Implementation readiness checklist

Before the implementation phase starts, the following facts should be true or
explicitly accepted as constraints:

1. `dev` and `candidate/dev` are aligned, or the implementation lane is rebased
   onto the current candidate head.
2. Active foreign lanes are classified by stage impact: observe-only during
   unrelated authoring; candidate blockers only when scope, proof, or baseline
   evidence overlaps; accepted-root blockers only when head-bound proof or
   closeout authority is not clean.
3. The implementation lane has a claim and bounded scope.
4. `ethos lane status --json` shows no unknown overlap for the implementation
   lane.
5. The first implementation slice changes only read-model/status surfaces unless
   a stricter gate is already proven by tests.
6. Any destructive-change policy work is deferred until ownership, epoch, and
   closeout authority are visible in command JSON.
7. Full proof failures are classified into current-lane failures versus foreign
   or baseline proof debt before any repair is attempted.
8. Status output distinguishes `authoring_allowed`, `integration_allowed`, and
   `accepted_closeout_allowed`, so concurrency is not sacrificed merely because
   a later-stage proof gate is red.

## Open decisions for maintainers

These are real design choices, not implementation details.

### Lane event envelope strictness

Option A: strict CloudEvents fields and naming.

- Pro: easier future interoperability.
- Con: may overfit a local repository lifecycle to a cloud event standard.

Option B: ETHOS lane event profile compatible with CloudEvents.

- Pro: keeps ETHOS semantics primary while preserving familiar fields.
- Con: future adapters may need a small mapping layer.

Recommendation: choose Option B now. Revisit strict CloudEvents only when an
external consumer needs it.

### Destructive-change carrier

Option A: extend existing claim / evidence schemas.

- Pro: avoids new entities.
- Con: claim schema may become broad.

Option B: add a small `destructive-change` schema linked from claim evidence.

- Pro: clearer for high-risk changes.
- Con: adds one new entity.

Recommendation: begin as claim/evidence extension. Add a separate schema only
if repeated destructive-change records make the claim schema unclear.

### Agent identity granularity

Option A: lane lease holder is enough.

- Pro: minimal entity count.
- Con: less detail about host/session identity.

Option B: add an agent registry.

- Pro: richer host/session tracking.
- Con: likely becomes a second truth source and stale quickly.

Recommendation: do not add an agent registry. Put host/session details inside
lease holder metadata and lane events. Reassess only if cross-host execution
requires durable agent identity beyond lane ownership.

### Runtime location

Option A: Git common-dir runtime state.

- Pro: shared by worktrees, not committed, local-first.
- Con: not visible after clone unless reconstructed.

Option B: tracked runtime-like files.

- Pro: portable.
- Con: pollutes history and creates merge conflicts.

Recommendation: use Git common-dir for active leases/events; promote only
selected evidence into tracked `evidence/` when it matters historically.

## Expert committee cadence for implementation

Each implementation slice should end with a short committee review:

1. **Kernel reviewer:** Did the change reduce to Work Lane, lease, scope, epoch,
   gate, log, claim, and evidence, or did it add unnecessary entities?
2. **Concurrency reviewer:** Can an old holder, foreign agent, stale worktree, or
   raw Git operation bypass the intended authority?
3. **UX reviewer:** Does the failed command tell an agent what it may do next?
4. **Creative-change reviewer:** Does the design permit net-positive destructive
   change instead of freezing the old structure?
5. **Evidence reviewer:** Is the completion claim backed by command output,
   tests, proof, or explicit documented limits?

A slice should not close if it only looks conceptually correct. It closes when
its authority, observability, and evidence surfaces agree.

## Current research-lane closeout note

This research lane is intentionally not forcing candidate integration or
accepted-root closeout while a dirty foreign lane is working on parity/proof
freshness:

- foreign lane: `work/parity-self-evidence-head`
- reason: it owns active changes in parity evidence, report/land support, and
  parity tests;
- implication: full proof failures involving parity should not be repaired in
  this lane unless ownership is explicitly transferred or that lane lands.

This is not an authoring blocker. The research lane remains useful and clean
because it only changes bounded research documentation:

- `docs/research/lane-lease-governance-research.md`
- `docs/research/lane-lease-governance-implementation-plan.md`

Once the parity lane lands or is otherwise resolved, refresh this lane onto
`candidate/dev`, rerun docs and proof gates, then land it through the normal
Work Lane path.
