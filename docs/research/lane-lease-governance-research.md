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

Primary source: https://kubernetes.io/docs/concepts/architecture/leases/

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

Primary source: https://etcd.io/docs/

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

Primary source: https://zookeeper.apache.org/doc/current/recipes.html

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

Primary source: https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/

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

Primary source: https://git-scm.com/docs/githooks

### GitHub / GitLab / Gerrit ownership and submit gates

Hosted code collaboration systems converge on three ideas: code ownership,
protected refs, and submit / merge gates. GitHub CODEOWNERS and branch
protection/rulesets, GitLab Code Owners and approvals, and Gerrit submit
requirements all separate authorship from authority to integrate.

ETHOS adaptation:

- Map code ownership to lane scope and claim ownership, not to hosted PRs as the
  local truth source.
- Treat closeout as a submit gate: owner / proof / candidate / overlap checks
  must pass before integration.
- Hosted PR/MR systems are publication surfaces, not the local source of truth
  for Work Lane lifecycle.

Primary sources:

- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue
- https://docs.gitlab.com/user/project/codeowners/
- https://gerrit-review.googlesource.com/Documentation/config-submit-requirements.html

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

Primary source: https://opentelemetry.io/docs/concepts/signals/

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

- https://cloudevents.io/
- https://cdevents.dev/

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

- https://slsa.dev/spec/v1.1/about
- https://in-toto.io/
- https://docs.sigstore.dev/
- https://scorecard.dev/

### OpenFeature and feature-flag discipline

OpenFeature provides a vendor-neutral feature flag API and specification. The
important architectural principle is decoupling deployment from activation.

ETHOS adaptation:

- Architectural or destructive migrations should prefer flags, shadow paths,
  compatibility modes, or branch-by-abstraction when a hard cutover would
  increase risk.
- Do not add a feature-flag SDK until runtime behavior genuinely needs it.
- Capture flag or shadow-mode evidence in the destructive-change record.

Primary source: https://openfeature.dev/specification/

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

- https://adr.github.io/
- https://rust-lang.github.io/rfcs/
- https://sre.google/workbook/error-budget-policy/
- https://dora.dev/guides/dora-metrics/
- https://principlesofchaos.org/

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

- https://modelcontextprotocol.io/
- https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- https://openai.github.io/openai-agents-python/
- https://docs.anthropic.com/en/docs/claude-code

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

## Recommended adoption matrix

| Mechanism | Decision | ETHOS form |
| --- | --- | --- |
| Kubernetes Lease | Borrow | holder + heartbeat + expiry |
| etcd revision / fencing | Borrow | lease epoch |
| ZooKeeper sequential session | Borrow | ordered explicit adoption |
| Redis Redlock | Do not adopt | cautionary TTL-only anti-pattern |
| Git reference-transaction | Adopt | protected ref gate |
| GitHub/GitLab/Gerrit ownership gates | Borrow | owner-only closeout and protected submit |
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
but integration into candidate / accepted root is a submit-like action requiring
proof, scope checks, and owner authority. CODEOWNERS-style ownership should
inform scope and review, but hosted PR/MR state must not become the local source
of truth.

Decision: borrow owner-only closeout, protected refs, submit queue semantics;
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
| GitHub/GitLab/Gerrit | No | Yes | Useful submit and ownership semantics; hosted systems remain publication surfaces. |
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
