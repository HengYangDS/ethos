# Authority, Intent, And Admission Boundary

## Why

The current multi-agent lease contract correctly rejects a provider label as a
lane owner, but it still conflates two different meanings of authority. In the
ETHOS kernel, Authority ranks truth sources and resolves conflicting facts; it
is not an IAM policy engine. Treating Authority as the component that grants
roles or capabilities would mix epistemic authority with operational
authorization and make the kernel less coherent.

The same contract also leaves room to over-promote a local Work Lane lease into
a cross-host security boundary. Local leases are valuable coordination facts,
but they cannot authenticate a caller or prevent a process controlled by the
same operating-system user from bypassing a local hook. The product needs to
state where coordination ends and where repository-transition admission begins.

## What Changes

- Clarify that Authority orders truth sources; authorization policy is a
  Commitment evaluated by admission for a concrete Change.
- Keep a concrete `holder_ref` in the local Lane Lease, but make the lease a
  coordination and stale-invocation detection mechanism rather than a
  capability grant, identity assertion, filesystem fence, or distributed lock.
- Distinguish requested intent and destructive confirmation from policy
  authorization: an `--apply` or legacy `--authorize` flag cannot authenticate
  its caller or satisfy permission policy by itself.
- Treat external identity and delegation assertions as optional, policy-required
  Evidence supplied through adapters. Do not create a Principal, Agent, Session,
  Team, or capability-grant registry in the ETHOS kernel.
- Place the strongest enforceable boundary at Git-native transition choke
  points: candidate integration, accepted-root movement, and publication.
- Require read models to expose the orthogonal decision basis actually proved
  instead of compressing identity, state binding, proof freshness, and local or
  hosted enforcement into one misleading assurance level.
- Replace actor-capability language in coordination previews with an explicitly
  non-authoritative action preview; bind actual mutation decisions to the
  canonical `allow | block | defer` verdict contract.
- Record only non-mechanical lane lifecycle judgments as Chronicle decision
  events; keep routine acquire, renew, accepted local handoff, deterministic
  owner retirement, heartbeat, and expiry in ignored local state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=authorization-admission-boundary;
  reuse=extend; change=modify; facet:lifecycle=runtime;
  facet:surface=cli,schema,docs; facet:authority=source,test,schema,docs,openspec,evidence

## Impact

The accepted repository-governance specification and canonical product design
language change. Subsequent runtime slices will affect local lease storage,
mutation-decision contracts, lane status, prewrite and retirement admission,
Git ref-move guards, and provider adapters. No external coordination service or
identity provider becomes a product dependency.

This is a **BREAKING** read-model vocabulary correction: compatibility fields
such as `current_actor_capability`, `allowed_actions`, and `forbidden_actions`
must be retired after consumers migrate to the bounded action-preview and
decision-basis contract.

## Out Of Scope

- No internal IAM, directory, user, team, Agent, Session, or Principal registry.
- No shared lease service, distributed lock manager, scheduler, mailbox, or
  agent orchestration platform.
- No claim that local hooks defend against a malicious process with equivalent
  filesystem and Git configuration authority.
- No requirement that routine offline lane authoring carry enterprise identity
  assertions.
- No automatic cleanup of foreign, dirty, missing-lease, or owner-unknown lanes.
