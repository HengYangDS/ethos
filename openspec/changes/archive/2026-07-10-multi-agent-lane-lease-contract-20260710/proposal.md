# Multi-Agent Lane Lease Contract

## Problem

ETHOS already separates Git authorship, Work Lane ownership, claims, evidence,
handoff, and break-glass policy. It also already exposes foreign Work Lanes as
observe-only and stores local lane leases. The remaining productization gap is
identity granularity: a lease owner string such as `codex` names a provider or
actor class, not the concrete agent instance that currently holds write
responsibility.

In a product setting, multiple humans, Codex threads, Claude chats, JetBrains
sessions, CI jobs, and service agents can operate in the same governed
repository. Treating all instances from the same provider as one owner makes
handoff, closeout, orphan audit, and residue retirement ambiguous. Adding a
separate Principal, Actor, Participant, or Session registry would solve the
symptom by turning ETHOS into an IAM or chat-session system, which violates the
single repository-kernel design.

## Change

Keep the kernel unchanged and make the existing Work Lane lease contract precise:

- Authority policy grants capabilities and roles.
- A Lane Lease grants temporary write ownership for a concrete holder.
- Chronicle records evidence-bound lane lifecycle judgments.

The lease holder is a provider-neutral `holder_ref` that identifies the concrete
acting instance, such as `agent:codex:thread:<id>`, `agent:claude:chat:<id>`,
`agent:jetbrains:chat:<id>`, `human:shell:<id>`, or
`service:gitlab-ci:pipeline:<id>`. Provider names such as `codex` remain provider
classes or legacy hints; they are not ownership identities.

Role and capability policy remains in Authority configuration. Handoff,
retirement, preserve, block, orphan audit, and break-glass outcomes are Chronicle
`lane_resolution` events bound to evidence. They do not create a second lifecycle
store.

## Scope

This change is a product contract and planning change. It updates the governed
repository design and OpenSpec requirements. It does not implement the full
runtime migration from `lease_owner` / `ETHOS_ACTOR` to `holder_ref` yet.

## Non-goals

- No Principal, Party, Participant, Actor, Session, or Agent registry as a new
  ETHOS truth center.
- No provider-specific ownership semantics.
- No chat, thread, mailbox, or message bus as repository truth.
- No automatic cleanup of foreign, dirty, missing-lease, or owner-unknown Work
  Lanes.
- No change to current head-bound retirement safety rules.
