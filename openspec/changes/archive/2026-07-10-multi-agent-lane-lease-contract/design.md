# Design

## Fixed point

The converged form is:

```text
Authority grants capability.
Lane Lease grants temporary write ownership.
Chronicle records evidence-bound lane judgment.
```

In Chinese shorthand:

```text
权在 Authority；
界在 Lease；
断在 Chronicle。
```

This is the smallest form that still supports a product repository operated by
many people and many agents.

## Why not Principal

`Principal` was considered and rejected as a first-class ETHOS object. It is an
IAM term, and productized organizations already have identity providers, teams,
users, service accounts, CI jobs, and host sessions. If ETHOS promotes Principal,
Actor, Participant, Party, Session, or Agent into its kernel, it becomes a
partial identity system and a second truth center.

ETHOS only needs to know whether a concrete holder currently has authority to act
on a lane, and why. That answer is derived from:

1. Authority policy;
2. the active Lane Lease;
3. claim and scope binding;
4. evidence and Chronicle decisions.

The durable product object is therefore not `Principal`; it is the existing
Authority plus a precise Lane Lease.

## Holder reference

A Lane Lease holder must identify the concrete acting instance, not merely the
provider. Recommended examples:

```text
agent:codex:thread:019f46b5-2ab0-7151-ad63-9ba0fffa1a71
agent:claude:chat:<id>
agent:cursor:session:<id>
agent:jetbrains:chat:<id>
human:shell:<id>
service:gitlab-ci:pipeline:<id>
```

The provider segment (`codex`, `claude`, `cursor`, `jetbrains`, `gitlab-ci`) is
only a class. The full `holder_ref` is the temporary lease holder. A bare provider
name such as `codex` is a legacy owner hint and cannot safely authorize foreign
retirement, handoff, or destructive cleanup in a multi-session product setting.

## Authority policy

Capability stays in Authority policy, not in the lease itself. The policy maps
identity references and patterns to roles and permissions. For example:

```toml
[roles.maintainer]
can = ["break_glass", "closeout_accepted", "retire_foreign"]

[roles.agent_author]
can = ["start_lane", "write_own_lane", "retire_own_clean_lane"]

[[identity]]
ref = "agent:codex:*"
roles = ["agent_author"]
```

The lease says who temporarily holds a lane. Authority says what that holder may
do. Claim, scope, proof, and Chronicle say whether the action is admissible.

## Lane resolution

`orphan` is not a persistent state. It is a verdict reached from evidence. The
same is true for handoff, retire, preserve, block, and break-glass. Durable
judgment belongs in Chronicle as a `lane_resolution` event, for example:

```json
{
  "event_type": "lane_resolution",
  "lane": "work/example",
  "kind": "handoff",
  "from_holder": "agent:codex:thread:A",
  "to_holder": "agent:claude:chat:B",
  "decided_by": "user:yheng",
  "evidence": ["git-head:<sha>", "proof-run:<id>"],
  "decision": "accepted"
}
```

This keeps lifecycle judgment append-only and evidence-bound without creating a
second lifecycle database. Dirty or owner-unknown lanes are protected: they may
be preserved or blocked, but not auto-deleted.

## Kernel mapping

No kernel expansion is needed:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

- Authority: role and capability policy.
- Subject: the governed repository and Work Lane subject.
- Commitment: Work Lane rules, claim obligations, and ownership policy.
- Change: lane authoring, integration, and retirement lifecycle.
- Evidence: Git head, dirty state, proof runs, scope, lease, and handoff facts.
- Claim: why the lane exists and what boundary it may change.
- Chronicle: accepted judgments about handoff, retire, preserve, block, or
  break-glass.

## Runtime migration sketch

The implementation path should be evolutionary:

1. Keep reading legacy `lease_owner` and `ETHOS_ACTOR` for compatibility.
2. Add `holder_ref`, `acts_for`, `epoch`, `heartbeat_at`, and `expires_at` to the
   lease payload or schema.
3. Treat `lease_owner` as a compatibility alias for `holder_ref` only when it is
   already concrete enough to identify an acting instance.
4. Add `ethos lane owner` / `ethos lane lease` reader views that expose holder,
   actor capability, and next legal action.
5. Add Chronicle `lane_resolution` events for handoff, retire, preserve, block,
   and break-glass.
6. Only after those are visible, migrate mutation gates from owner-string match
   toward holder-ref plus Authority-policy checks.

## Invariants

1. Provider is not owner: `codex` is not equivalent to
   `agent:codex:thread:<id>`.
2. No valid lease means observe-only for tracked mutation.
3. Authority policy decides capability; leases do not grant maintainer power.
4. Claim and scope decide land boundary; a lease alone does not make a change
   trust-bearing.
5. Chronicle records lifecycle judgment; destructive cleanup without Chronicle
   evidence has no durable claim.
6. Dirty unknown lanes are protected.
7. Orphan is an evidence-bound resolution, not a standing state.
8. Host messages, IDE sessions, and chat threads are projections unless promoted
   into repository truth, evidence, claim, or Chronicle.
