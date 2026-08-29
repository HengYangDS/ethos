## Context

The terminal protocol is:

```text
fresh observe -> compile TransitionPlan -> effect-time recheck -> exact CAS
-> post-observe -> Attestation -> recover or compensate
```

The current implementation splits that protocol among `git_effects`,
`ref_intent`, the reference hook, Lease transition code, worktree effects, and
lifecycle-specific recovery modules. That split is downstream of a more basic
model error:

- official OpenSpec and tracked `commitment.toml` both own intent;
- Lease payloads copy moving Git and Commitment coordinates;
- predecessor/successor fields persist a lineage that Git already records;
- hypothesis, falsifier, and experiment-protocol fields turn design work into
  a second schema and lifecycle.

The most damaging runtime symptom is ordinary Work Lane ref movement: the
hook's committed phase mutates `Lease.expected_head` and `expected_tree`. A
crash or hook failure after Git commits the ref therefore creates
valid-but-stale authority even though the ref itself is already the current
repository fact.

Git 2.55 subprocess evidence also establishes that `git merge --ff-only` and
`git checkout -b` can update the index and worktree before a prepared
reference-transaction rejection. The ref hook is atomic only for refs.

## Decision

### Official OpenSpec owns authored intent

The official OpenSpec Change projection is the only tracked authored intent.
ETHOS compiles one immutable Commitment value from the exact official
requirements and scenarios selected from a Git tree. The compiled value exists
to bind acceptance and proof; no author maintains a second TOML carrier.

Commitment contains no anticipated path scope, authority refs, risk register,
progress, predecessor/successor ledger, dependency graph, hypothesis DSL,
falsifier DSL, or experiment protocol. Changed paths and Git coordinates are
fresh Facts. A prerequisite matters to the kernel only when an exact prior
Attestation changes current admission, in which case that Attestation is an
input to the current TransitionPlan.

Ordinary before/after history is queried from Git and archived OpenSpec.
"Successor" is therefore a query result, not a stored object or lifecycle.
Hypotheses and experiment procedures remain prose and tasks in official
OpenSpec. Exact observations and conclusions are Attestations; they do not
create an experiment state machine.

### One local repository-effect owner

`execute_git_effect` is the sole local ref executor. It owns the exact effect
capability, effect-time observation, ref CAS, postcondition, effect
Attestation, and exact ref-only compensation/recovery. Callers compile semantic
operations into the same `TransitionPlan`; they do not implement another ref
transaction.

Worktrees, indexes, hooks, and runtime files are rebuildable projections, not
members of the ref transaction. After an attested ref effect, callers converge
their projection forward with idempotent exact worktree effects. A projection
failure never rewinds an already attested ref. Retrying the same public command
recognizes the Attestation and completes only the missing projection.

The hook consumes the executor-issued exact intent in `prepared`, then observes
`committed` or `aborted`. It does not update Lease, persist an effect receipt, or
perform lifecycle recovery.

### Lease is a coordination relation, not repository authority

A Lease generation binds only lane incarnation, holder, CAS generation, and
expiry. Current branch HEAD and tree, selected official OpenSpec projection,
compiled Commitment, index, and changed paths are fresh Facts bound by each
admission or TransitionPlan. Ordinary commits do not rewrite Lease merely to
mirror the current ref.

Transitions that actually change authority still replace the Lease generation:
start, holder transfer, takeover, renewal, and retirement. They bind their own
exact pre/post coordinates in the TransitionPlan and Attestation. Commitment
"rebind" and Change "succession" disappear because neither is a Lease concern.

### Raw Git fail-clean boundary

Protected integration mutation belongs to the ETHOS command plane. Defense-in-
depth hook rejection may compensate an already projected checkout only when:

- current HEAD is still the pre-effect HEAD;
- index tree exactly equals the rejected target commit tree;
- worktree exactly equals that index; and
- restoration post-observes the original HEAD tree.

Any non-exact overlay is not reconstructed or discarded. The hook reports the
blocked effect and leaves explicit recovery to the command plane.

## Deletion

- Delete every tracked `commitment.toml`, its parser/schema/formatter, and
  authoring commands that exist only to maintain it.
- Delete Commitment fields and value types for scope, predecessor/successor,
  dependencies, hypotheses, falsifiers, experiment protocols, authority refs,
  risk, and progress unless an acceptance compiler proves the field changes an
  acceptance proposition.
- Delete predecessor-resolution, successor-commitment, successor-recovery, and
  private commitment-rebind command/effect/receipt/recovery machinery. Keep no
  alias, dual reader, fallback, or compatibility facade.
- Delete Lease payload copies of Git, Commitment, scope, handoff workflow, and
  effect outcome. Keep one minimal row for lane, holder, generation, and expiry.
- Delete committed-phase Lease advancement from the reference hook.
- Delete Lease HEAD/tree equality as current authoring authority after all
  consumers use fresh Git and official OpenSpec facts plus the minimal Lease.
- Delete lifecycle-specific ref compensation/recovery once the unique executor
  owns equivalent semantics.
- Delete projection callbacks and reverse-ref recovery used to simulate one
  transaction across Git refs and rebuildable host state.
- Delete the unsupported `preparing`/`ORIG_HEAD` interception assumption.

### Entity admission rule

Before adding a durable entity, field, receipt, lifecycle, or owner, answer all
three questions affirmatively:

1. Can official OpenSpec, Git facts, the minimal Lease, TransitionPlan, or an
   Attestation already express it?
2. Would deleting it make a required invariant impossible to prove?
3. Does it have one unique owner, consumer, and terminal deletion/retention
   rule?

Any negative answer forbids the entity.
