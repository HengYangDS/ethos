---
subject: ethos:lane-lease-governance-implementation-plan
role: plan
state: experimental
relations: implements: ethos:lane-lease-governance-research; supports: lane lease governance, net-gain destructive change governance
updated: 2026-07-06
---

# Lane Lease Governance Implementation Plan

## Purpose

This plan turns the Lane Lease Governance research intake into an executable
sequence. It preserves the central constraint: ETHOS should protect foreign
Work Lanes from unauthorized mutation while allowing owned lanes to carry bold,
net-positive, even destructive change when bounded and evidenced.

The implementation should not begin by adding a large coordination subsystem.
It should strengthen the existing Work Lane lifecycle through observable status,
lease fencing, lane-local events, and proof-backed closeout.

## Non-negotiable invariants

1. Foreign Work Lanes are observe-only unless ownership is transferred or a
   maintainer adopts them through an explicit command.
2. A stale lease is not an abandoned lane. It only creates a handoff/adoption
   decision point.
3. Destructive change is permitted inside an owned and declared scope when it
   has a net-gain hypothesis, blast radius, rollback, abort condition, and
   evidence target.
4. UI, IDE badges, dashboards, and agent prompts are projections. They must not
   become second truth stores.
5. `ethos status --json`, `ethos lane status --json`, `ethos lane prewrite`,
   proof, and closeout gates are the authoritative command surfaces.
6. Reference hooks are the substrate fallback; user-facing commands should fail
   earlier with useful next actions.
7. Work Lane authoring, candidate integration, and accepted-root closeout are
   separate stages with separate proof burdens. A red integration or closeout
   gate must not unnecessarily serialize unrelated lane-local authoring.

## Stage gates: authoring, integration, closeout

The lane system should preserve high parallelism:

- **Authoring gate:** checks lane ownership, declared scope, and prewrite
  legality. It allows local design, focused tests, and evidence preparation.
- **Candidate integration gate:** checks overlap, baseline parity, candidate
  freshness, cross-lane proof debt, and net-gain evidence for disruptive
  changes.
- **Accepted-root closeout gate:** checks candidate proof, expected head,
  sanctioned ref movement, and historical evidence.

The read model should expose these states independently:

```json
{
  "authoring_allowed": true,
  "integration_allowed": false,
  "accepted_closeout_allowed": false,
  "blocker_owner": "work/parity-self-evidence-head"
}
```

This keeps Work Lanes generative while preserving a strict candidate train and
accepted history.

## Slice 0: classify current parity/readmodel lanes

Before coding, inspect current repository truth.

Required checks:

```bash
ethos lane status --json
git branch --list 'work/*' -vv
git worktree list --porcelain
git rev-list --left-right --count dev...candidate/dev
```

If a foreign lane owns parity, coordination read models, or workspace-status
schema changes, do not duplicate that work. Classify its impact by stage:

- unrelated authoring can continue in the owned lane;
- integration waits when scope, baseline proof, or parity evidence overlaps;
- accepted-root closeout waits until candidate proof is clean.

Acceptance:

- no overlapping dirty foreign lane for the intended authoring write scope;
- current lane rebased onto current `candidate/dev`;
- proof failures classified as current-lane, baseline, or foreign-lane debt;
- status or planning output names which stage is blocked: authoring,
  integration, or accepted closeout.

## Slice 1: discoverable authority read model

Goal: make legal action visible before adding stricter enforcement. This is not
cosmetic polish; discoverability is the first safety and productivity primitive
for both humans and agents.

Candidate files after scope review:

- `src/ethos/adapters/repo/coordination.py`
- workspace status schema
- lane status tests
- CLI contract tests
- command help / rendering tests where available

Required behavior:

- status reports `actor_role`: owner, observer, maintainer, protected-root;
- status reports `allowed_actions` and `forbidden_actions`;
- status separately reports `authoring_allowed`, `integration_allowed`, and
  `accepted_closeout_allowed`;
- status reports one deterministic `next_action` while retaining all gaps and
  capabilities as facts;
- status reports blocker stage, blocker owner, and whether the blocker is
  authoring, candidate integration, or accepted closeout;
- foreign lanes render observe-only authority with disjoint/overlap state;
- stale or unknown ownership reports next legal commands;
- root/editor-root ambiguity is visible in JSON and human output;
- command help, error text, JSON keys, and docs use the same nouns.

Tests:

- accepted root shows observe-only for normal mutation;
- owned lane shows write/prewrite/land capability;
- foreign lane shows read/diff/note/request-handoff only;
- stale lease does not imply delete/retire permission;
- human rendering includes role, capability, stage gate, and next command;
- JSON contract is stable enough for Codex/Claude/MCP adapters.

Expert review questions:

> Does the read model tell an agent what it may do without reading prose docs?
> Could a human contributor recover from the same output without knowing ETHOS
> internals?

## Slice 2: lease epoch and fencing

Goal: prevent old or resumed holders from mutating after ownership changes.

Required behavior:

- lease carries `epoch`;
- owner transfer/adoption increments epoch;
- prewrite checks holder and epoch;
- land/closeout checks holder and epoch;
- stale heartbeat alone never grants mutation.

Likely invalid states:

- `lease_missing`
- `lease_holder_mismatch`
- `lease_epoch_stale`
- `stale_lane_without_adoption`
- `foreign_lane_write`
- `foreign_lane_closeout`

Tests:

- old holder fails after adoption;
- new holder succeeds after epoch bump;
- stale but unadopted lane cannot be deleted;
- adopted lane records new holder and epoch.

Expert review question:

> Can a paused agent resume and still write after another holder adopts the lane?

## Slice 3: lane-local event profile

Goal: add coordination without an agent-to-agent mailbox.

Event profile:

- CloudEvents-compatible fields: `id`, `source`, `type`, `subject`, `time`,
  `data`;
- `subject` is the Work Lane;
- `source` is the repository / ETHOS command plane;
- `data` carries holder, epoch, state, reason, and next action when relevant.

Initial event types:

- `lane.created`
- `lane.scope.declared`
- `lane.handoff.requested`
- `lane.adopted`
- `lane.blocked`
- `lane.proof.executed`
- `lane.landed`
- `lane.retired`

Runtime location:

- Git common-dir runtime state for active events;
- tracked evidence only when an event matters historically.

Tests:

- lane start emits or records creation;
- handoff/adoption/blocked events are append-only;
- events do not override lease state;
- status can summarize recent relevant events without requiring a dashboard.

Expert review question:

> Is communication lane-centered rather than agent-centered?

## Slice 4: net-gain destructive-change admission

Goal: encourage creative, structural improvement while bounding harm.

Change classes:

- `routine`: ordinary proof;
- `material`: ADR-style rationale;
- `destructive`: RFC-style proposal plus guardrails.

Destructive-change required fields:

- intent: what old structure is being broken;
- hypothesis: what improves;
- blast radius: files/modules/runtime paths affected;
- rollback: exact recovery route;
- abort condition: when to stop;
- net-gain metric: evidence that improvement is real;
- archive target: where result or failure is recorded.

Tests:

- routine change not forced through ADR/RFC;
- destructive change without rollback is blocked;
- destructive change outside owned scope is blocked;
- destructive change with full record is admitted inside owned lane;
- failed bounded experiment can be archived as knowledge, not silent success.

Expert review question:

> Does the policy allow breaking obsolete structure, or merely protect the old order?

## Slice 5: protected ref fallback

Goal: prevent raw Git bypass after command UX is clear.

Protected refs:

- `refs/heads/work/*`
- `refs/heads/candidate/*`
- accepted root branch

Required behavior:

- raw delete/move of active Work Lane is rejected;
- raw accepted-root movement is rejected;
- sanctioned ETHOS retire/closeout works with expected head and authorization;
- hook fails closed when command context cannot be proven.

Tests:

- direct `git branch -D work/foo` rejected for active lease;
- official `ethos lane retire-landed` accepted;
- direct accepted-root update rejected;
- official closeout accepted.

Expert review question:

> Are hooks a fallback guard rather than the primary UX?

## Slice 6: projection and DX polish

Only after command JSON and human rendering are correct:

- concise human `ethos lanes` view if it reuses the Slice 1 read model;
- IDE badge projection;
- shell-completion or command-suggestion affordances if they reuse command
  metadata;
- optional local dashboard;
- MCP resource projection if useful.

Projection rule:

> Projection may display and initiate ETHOS commands, but may not own lifecycle
> truth. Projection improves discoverability; it does not define authority.

## Verification ladder

Each slice should use the narrowest meaningful proof first, then graduate:

1. focused unit tests for the changed surface;
2. lane-local CLI contract tests;
3. docs-registry/schema checks if docs/schema changed;
4. `ethos lane status --json` from accepted root and owned lane;
5. lane-local proof for authoring readiness;
6. candidate proof only at integration time;
7. accepted-root closeout only when candidate proof is clean and expected-head
   authority is current.

## Closeout criteria for this implementation plan

This plan is complete when it is landed as research/design input and the next
implementation lane can start from current `candidate/dev` with:

- no overlapping dirty foreign lane in the selected authoring scope;
- a bounded claim;
- explicit file scope;
- expected tests and proof gates listed by stage;
- expert committee review questions attached.
