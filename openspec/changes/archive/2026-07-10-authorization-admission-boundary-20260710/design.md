# Design

## Context

ETHOS has one kernel chain:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

The previous multi-agent contract correctly distinguished a concrete Work Lane
holder from a provider label, but assigned role capability to Authority and left
the Lane Lease open to interpretation as an identity or permission grant. Both
are category errors:

- Authority ranks competing sources of repository truth.
- A Commitment states policy and obligation.
- Admission is a pure evaluation of one requested Change against current facts.
- A Lane Lease is ignored local coordination Evidence.
- Chronicle retains only judged outcomes that must survive local-state loss.

Current runtime compares self-declared `ETHOS_ACTOR` and `lease_owner` strings and
can retain more than one active lease row for a lane. That is useful cooperative
guarding, not authentication, exclusive distributed ownership, or hard
filesystem fencing.

## Goals / Non-Goals

### Goals

- Preserve the seven-node kernel without adding IAM or coordination ontology.
- Separate intent, confirmation, authorization, admission, and enforcement.
- Make local multi-agent ownership concrete, exclusive, resumable, and safe to
  hand off without overstating what a local lease can enforce.
- Put strong claims at the Git ref boundaries that actually mediate transitions.
- Keep normal lifecycle local and durable exceptional judgment reviewable.

### Non-Goals

- No Principal, Agent, Session, Team, credential, or capability-grant registry.
- No distributed lock, scheduler, mailbox, or orchestration service.
- No claim that a same-user local process cannot bypass hooks or write files.
- No enterprise identity requirement for every offline edit.
- No automatic deletion of dirty, foreign, ambiguous, or owner-unknown work.

## Decisions

### 1. Authorization is a bounded decision, not an Authority object

Authority answers which source wins a conflict about repository truth; it does
not authenticate a caller or issue permission. Operational authorization is
represented without another kernel node:

```text
Commitment defines the obligation;
Change identifies the requested action;
Evidence supplies Git, lease, proof, and identity facts;
admission returns allow | block | defer for the exact bound request;
Chronicle records selected durable judgments.
```

Intent and confirmation remain distinct. `--apply` selects execution rather
than planning. A destructive confirmation records acknowledgement of one
side-effect; legacy `--authorize` must not be treated as identity or permission
and should converge on confirmation vocabulary.

A mutation decision binds action, resource, expected mutable state, policy refs,
evidence refs, and decision basis. It grants no reusable role, session, token, or
capability. A current user instruction may supersede lower-authority meaning in
the active reasoning context, but an unverified prompt becomes neither durable
policy nor machine authentication; any resulting waiver or policy change still
passes repository mutation and transition controls.

Control-plane changes cannot approve themselves. When authorization policy,
proof floors, admission code, owner scripts, identity trust, or enforcement
adapters change, accepted incumbent controls run from incumbent or protected
external provenance; candidate controls separately prove candidate conformance.
First policy adoption requires a bootstrap approver and verifier configured
outside the candidate tree. If incumbent or bootstrap provenance is unavailable,
the transition defers rather than trusting candidate code.

### 2. External identity is Evidence; Holder is local coordination

`holder_ref` is a structured, provider-neutral value naming the concrete local
execution instance responsible for a lane. Its kind, namespace, instance kind,
and opaque ID support equality and handoff; no segment implies privilege.
`agent:codex:thread:<id>` is one serialization, not an Agent ontology.

Where a Commitment requires organization or workload identity, an adapter
verifies the minimum issuer-qualified assertion required for that action:
identity reference, issuer, audience, verification method, validity interval,
optional delegation, and attestation digest. An attestation is a verifiable
issuer statement, not the underlying real-world fact and not permission by
itself. Credentials, bearer tokens, unnecessary personal data, and account
profiles never enter repository truth.

Routine offline lane authoring needs no enterprise assertion unless the
repository Commitment says otherwise. `ETHOS_ACTOR`, `lease_owner`, display
names, and bare provider labels remain migration hints only; they cannot admit
foreign retirement, break-glass, accepted closeout, or publication.

### 3. Lane Lease is one-writer local coordination

The lease is scoped to one Git common directory and remains under ignored local
state. It is not a cross-clone lock or durable truth. The normalized current
record contains:

```text
lane_incarnation_id  # random local ABA boundary
lease_id
lane_ref
holder_ref
epoch
issued_at
renewed_at
expires_at
claim_id?
path_scope?
```

One lane incarnation has at most one current writer holder. Separate concurrent
writers use separate Work Lanes. SQLite compare-and-swap governs lease create,
renew, resume, and handoff:

- renewal keeps holder, lease ID, and epoch;
- accepted handoff changes holder and increments epoch;
- the prior holder may resume an expired lease only with its prior lease ID,
  epoch, unchanged expected head, and no contrary accepted judgment;
- another holder never acquires an existing lane merely because a lease expired;
- deletion and recreation receive new lane-incarnation and lease IDs;
- duplicate, provider-only, missing, or ambiguous legacy leases fail closed.

Epoch is an optimistic stale-invocation check, not a filesystem fencing token.
Normal ETHOS mutation paths compare the invocation's expected holder, lease ID,
epoch, and head immediately before mutation. Handoff is offer/accept within one
common directory and includes holder quiescence; uncertainty or post-handoff
residue blocks integration. No local mechanism proves that an already-running or
bypassing same-user process stopped.

Git branch/worktree and SQLite changes are a crash-consistent saga, not one
transaction. Each operation binds expected pre-state, executes the smallest
atomic step, verifies postconditions, retries idempotently where safe, and makes
partial state visible for repair. Local lease, offer, attempt, and receipt data
have declared retention; unresolved ambiguity remains until repair rather than
being silently swept.

Cross-host handoff transfers content-addressed Git state plus a digest-bound
context or recovery carrier, never the source SQLite lease. Dirty tracked and
untracked work is classified and committed or preserved explicitly; Git stash
and chat transcripts are not handoff carriers. The destination creates a new
local lane incarnation and acknowledges it before the source revokes its writer
lease or retires its retained observe-only copy.

Legacy adoption is explicit. A provable current holder may normalize that same
holder and head. Provider-only, owner-unknown, dirty-unknown, missing, or
ambiguous state requires an accepted maintainer decision that pre-binds the new
incarnation ID, exact target observation, disposition, and recovery plan; apply
cannot invent and authorize its own target identity.

### 4. Strong claims belong to mediated truth transitions

Independent clones may author independently. Local candidate and accepted refs
are local truth horizons; the remote old/new ref update is the shared cross-host
publication horizon. Each transition binds its expected heads and evidence and
fails stale conflicts instead of requiring a distributed lease.

Decision output is factored rather than ranked:

- `enforcement_boundary`: where the verdict could prevent the transition;
- `identity_basis`: how the invoker was identified;
- `state_bindings`: root, role, paths, lease generation, HEAD, and ref values;
- `evidence_boundary`: readiness, executed proof, hosted observation, or
  publication evidence;
- `verifier_provenance`: candidate, incumbent, protected provider, or unknown;
- `time_basis`: observation time and validity source for freshness claims.

These axes do not compensate for one another and are not a trust score. Strong
identity cannot repair stale proof; a HEAD-bound proof does not identify a
caller; local evidence is not hosted evidence. Coordination readers return a
non-authoritative `action_preview` with `mints_authority=false` and
`recheck_required=true`; actual mutation always re-evaluates its exact request.
Legacy actor-capability fields are retired after client migration.

An enforcement prevention claim is conditional: the configured boundary must
actually mediate every relevant ref transition, with coverage and provenance
shown by a server-side or equivalent enforcement receipt. A local hook, CI file,
or provider template proves configuration intent only. Unknown or bypassable
coverage reports no prevention claim. Local accepted readiness and remote
publication therefore remain distinct.

### 5. Chronicle records exceptional judgment, not telemetry

Routine acquire, renew, resume, accepted handoff, clean landed owner retirement,
heartbeat, expiry, and ordinary allow/block/defer receipts stay local. Chronicle
records only interpretive decisions that must survive local-state deletion:
preserve, block, orphan recovery, foreign-retirement authorization,
non-mechanical supersession, disputed handoff, and break-glass reconciliation.
Under the current schema these are `event_type=decision` records whose decision
value names `lane_resolution/<kind>`; there is no second resolution store.

Exceptional cleanup is normally two-phase. An owned governance Work Lane first
promotes a decision binding policy, evidence, exact head, lane-incarnation
digest, and a target-observation digest covering worktree, tracked and untracked
state, lease, accepted relation, observation time, and verifier. Cleanup then
recomputes those mutable facts and consumes the already accepted decision. The
decision authorizes an effect; only postconditions prove what was actually
removed. Any mismatch requires a new decision.

Break-glass is the narrow exception to prior promotion, not to evidence or
accountability. A predeclared Commitment binds verified maintainer identity,
exact target/head, reason, blast radius, expiry, preservation default, and
postcondition plan. Emergency action emits a digest-bound receipt and blocks
later integration/publication until a separate Work Lane promotes post-hoc
judgment and reconciles residue. Dirty or unknown work is isolated and preserved
by default; irreversible deletion still requires an accepted decision proving
the exact recovery disposition.

## Rejected Alternatives

- **Principal/Agent/Session registry:** duplicates enterprise identity and
  creates a second authority center.
- **Authority as permission engine:** collapses truth precedence into IAM.
- **Persistent capability grants:** introduce issuance and revocation state that
  current action-specific evaluation does not need.
- **Distributed Lane Lease:** duplicates Git ref serialization and turns ETHOS
  into an orchestration service.
- **Epoch as hard fencing:** the worktree filesystem does not enforce it.
- **Candidate controls approving themselves:** lets weakened candidate policy
  manufacture its own admission.
- **Chronicle for every event:** turns judged memory into local telemetry.

## Migration

1. Correct canonical docs/specs and separate intent, policy, admission,
   enforcement, and evidence vocabulary.
2. Normalize the local lease record and lifecycle with fail-closed legacy reads,
   explicit resume/handoff/adoption, and crash-consistent repair states.
3. Expand mutation decisions and reader previews with request binding and
   factored decision basis; remove owner-string authorization.
4. Bind control-plane replacement to incumbent provenance and define external
   identity/bootstrap/hosted-enforcement adapters without making them defaults.
5. Add the two-phase exceptional resolution and bounded break-glass paths while
   keeping routine lifecycle local.

Each slice keeps Git as repository truth and local coordination rebuildable.
Provider formats remain adapter choices; no ontology question remains open.
