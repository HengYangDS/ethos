---
subject: ethos:runner-mutation
role: explanation
state: canonical
relations:
  canonical_for: workspace execution boundary
---

# Runner And Mutation Boundary

ETHOS separates planning from execution. The kernel emits TransitionPlan; the
workspace layer chooses a runner.

Initial runners are deliberately small:

- `DryRunRunner` records the action without side effects.
- `LocalSubprocessRunner` executes a node in a chosen repository root.
- Future Dagger, hosted CI, Temporal, or remote agent runners must consume the
  same TransitionPlan contract.

Tracked mutation is gated by a mutation decision. `ethos land --apply` and
`ethos publish --apply` require explicit authorization and an expected HEAD.
Without both, the command returns `authorization_required` or
`expect_head_required` instead of mutating.

Tracked file edits must pass Work Lane admission before an agent writes. `ethos
lane start` creates an owned Work Lane branch under the configured prefix,
binds it to a linked worktree, and records a local lease. `ethos lane status`
exposes linked worktrees and foreign Work Lanes from the accepted root without
entering those foreign worktrees. `ethos lane prewrite` rejects tracked writes
from protected roles and requires the editor root to match the owned Work Lane.
The write boundary is deliberately ordered: target path, repository root,
context refresh, status, prewrite, write, then post-write audit. This order keeps
mutation bound to repository truth instead of a shell cwd, editor tab, or agent
host assumption.

The local candidate train is the configured candidate branch bound to its own
linked worktree. `ethos lane candidate --apply` bootstraps that worktree from a
clean accepted root with an expected HEAD. New Work Lanes start from the
candidate branch instead of the accepted root, and `ethos land --apply` from an
admitted Work Lane fast-forwards the candidate worktree without advancing the
accepted root. `ethos land --json` checks the same ancestry before mutation; if
the candidate train has advanced since the Work Lane started, it reports
`candidate_base_stale` and points to `ethos lane refresh-base` instead of
waiting for apply mode to discover the stale base. If the candidate train and
accepted root diverge before accepted-root closeout, closeout reports
`candidate_diverged_from_accepted` and points to
`ethos lane candidate --refresh-from-accepted --apply --authorize --expect-head <head> --json`
so the train can be reset deliberately before the Work Lane is replayed.
Status output reports configured `role_policy` and role-policy
`branch_bindings` in semantic order:
release_root -> accepted_root -> candidate -> work_lane -> proposal_lane.
Existing linked worktrees report `worktree_binding = "linked"` as product
state; host-specific navigation labels are adapter projections, not workspace
semantics. Adapters derive presentation from `worktree_binding`; they do not
own branch role, lane, or mutation semantics.
Foreign Work Lanes appear once in `foreign_work_lanes`; unbound refs appear in
`unbound_work_lane_refs`, and derived contention appears in `coordination_gaps`.
No coordination package persists duplicate counts or lifecycle state. Presence
is advisory when scopes are disjoint or the current checkout
is observe-only. Candidate integration from a Work Lane is blocked by required
coordination gaps for the current lane, such as unknown current scope. Foreign
unknown scope and same-file/ancestor-scope overlap are surfaced as advisory
`coordination_gap:*` contention, leaving Git's fast-forward land as the final
mutation arbiter without serializing unrelated agents that merely share a
directory.
`ethos lane start --apply --json` returns the newly created Work Lane under
`data.worktree` with the same binding vocabulary. Start admission also rejects a
dirty candidate worktree with `candidate_worktree_dirty`, so a new Work Lane
cannot be created from ambiguous local candidate state. When a Work Lane lands
to the candidate train, ETHOS carries the already verified HEAD-bound executed
proof record into the candidate worktree's local proof state. This carry-forward
is not a new proof minting path: the source record must verify before copying,
and the target copy is re-verified after writing. This projection is internal;
the public mutation result returns the Git-effect attestation rather than a
second proof-carry receipt. The projection exposes
`truth_boundary = "local-proof-state-projection"`,
`mints_proof = false`, `same_head_only = true`, and source/target verification
flags. It simply keeps Evidence with the same promoted HEAD so accepted-root
closeout can prove the candidate head without requiring a redundant runner pass.
The standard Work Lane lifecycle is command-bound: `ethos lane start` consumes
an explicit Commitment for a fresh Change, or a source Work Lane's exact
Lease-bound Commitment only when continuation is explicitly requested. It
creates the lane and binds the new Lease to the resulting HEAD, tree, carrier
path, carrier-byte SHA-256, and semantic digest. Missing, ambiguous, or
mismatched Commitment coordinates block before any ref, worktree, or SQLite
effect. `ethos lane
refresh-base` replays a stale lane onto the configured candidate branch, `ethos
lane repair-identity` handles the narrower case where a trusted re-sign changes
only the commit signature headers and OID: it binds the current holder, Lease,
exact HEAD/tree, fresh proof, repository-external signature trust, and unchanged
unsigned commit payload, then advances candidate, accepted, and any configured
release mirror through exact CAS. It never authorizes a general non-fast-forward
rewrite; an interrupted post-CAS worktree projection is completed by an
identical retry. `ethos
land` advances the configured candidate branch, and `ethos lane retire landed`
removes only an explicitly named clean landed Work Lane at the expected Work
Lane HEAD. `ethos lane retire superseded` also lets the current clean, leased
successor retire one clean, ownerless source whose exact HEAD is its ancestor;
the transaction preserves both accepted and successor refs and retains the
successor Lease. Prewrite, TransitionPlan, proof, head advance, handoff,
closeout, retirement, and status all consume the same strict Lease observation
and exact carrier binding. Cross-host source revocation is likewise an exact
live-Lease CAS: a missing Lease blocks and never masquerades as successful replay.

`ethos lane archive-change` closes the lifecycle edge that cannot be split
between an external archive process and a later Git commit. It requires the
same-holder exact Lease and proof for the pre-archive HEAD, runs official
OpenSpec `1.7.0`, admits only its exact rename/spec delta, commits through the
ordinary hooks, advances the Lease to the archived carrier, and attests the
post-state. The archived HEAD remains plan/proof/land capable without restoring
an active carrier or bypassing hooks.
Unbound Work Lane refs are observations only. Status preserves their exact ref,
HEAD, complete Lease generation, and accepted-relation facts, but no lifecycle
command deletes them.
Unknown, dirty, unbound, or owner-uncertain state remains blocked until a future
generic recovery Commitment is independently admitted. Raw Git worktree
creation can exist as a repository fact, but it is not standard ETHOS workflow
state.

Status output also carries `closeout_support`. Only the current clean
Work Lane checkout can advertise `operation = "land_to_candidate"`. Release
roots, accepted roots, candidate branches, proposal lanes, detached heads, and
foreign Work Lanes remain observe-only and report blocking gaps such as
`protected_root_mutation`, `work_lane_dirty`, `candidate_worktree_missing`, or
`candidate_worktree_dirty`.

Accepted-root closeout is the matching protected-root mutation. It runs through
the ETHOS command plane from a current ETHOS runner:

```bash
ethos land --closeout --apply --authorize --expect-head <accepted-head> --root <accepted-root> --json
```

The command audits the configured candidate worktree first, requires executed
proof for the candidate head being promoted, and only then fast-forwards the
accepted branch from the candidate branch. The accepted root's `--expect-head`
remains a substrate freshness guard; it is not the semantic proof target of the
closeout change. The `closeout_bootstrap` package in
`ethos land --closeout --json` records the accepted root, audit root, configured
branches, heads, `proof_target`, blocking gaps, exact command, and
`runner_binding` package so the handoff is product state rather than a host UI,
assistant runtime, or shell convention. The runner binding exposes the current
runner module path, package path, source root, and whether that source root
matches the accepted or audit root; mismatches are advisory signals, not a
second truth store. Its mode is `maintainer_break_glass_local`: a current ETHOS
runner is allowed to execute the protected closeout with an explicit
`--root <accepted-root>`, while remote push remains `deferred` and the candidate
worktree is audited and proven before accepted-root movement.

When a candidate changed a control path and needs a protected external bootstrap
receipt, the candidate-proof input is the native JSON result of
`ethos prove --execute --json`. The verifier requires `command = "prove"`,
`verdict = pass`, `state = "proven"`, `data.executed = true`, and matching candidate
HEAD bindings at `data.evidence.head` and
`data.provenance.predicate.head`. A hand-written `{head, state}` envelope is
not a proof record. This keeps the bootstrap adapter bound to the product proof
contract without adding a profile, provider, or adopter-specific branch.

ETHOS does not ship the executable that makes this operator decision. The
the independent provider emits the signed
`system/schemas/kernel/independent-verification-receipt.schema.json` receipt into
its protected receipt store. The receipt is supplied explicitly through
`--independent-verification-receipt`. Product admission rechecks the exact
accepted and candidate HEADs, changed control paths, both control-tree digests,
the executed-proof digest, provider implementation digest, and signature,
and bootstrap decision bindings before allowing closeout. The receipt is one-shot,
mints no authority, and does not claim cryptographic independence from the local
OS identity boundary described in DR-0006; stronger trust anchors remain an
operator deployment choice.

If the accepted root and candidate branch already resolve to the same HEAD,
closeout is current rather than ready-to-mutate. `ethos land --closeout --json`
reports `state = "accepted_current"`, `closeout_bootstrap.state = "current"`,
and `ethos publish` as the next action. Apply mode is a no-op in that state: it
still requires `--authorize` and `--expect-head` as mutation-safety intent, but
it does not require a new candidate proof because no new candidate head is being
promoted.

`ethos publish` is a local readiness command until a remote publication adapter
is available. It reports `remote_push = "not_performed"`,
`summary.remote_publication_state = "deferred"`, and a
`publication.mode = "local_readiness"` package with the planned proposal branch
under the configured proposal prefix. Remote reachability is reported separately
under `remote_availability.state`; an available remote does not mean remote push
or hosted CI has been performed. Remote push is deliberately deferred; local
proof and candidate closeout are still the required preparation.

The publication payload also carries `publication.local_proposal_package`, a
non-blocking package that records the source branch, planned proposal branch,
deferred remote state, and required local steps: land the Work Lane to the
candidate branch, fast-forward the accepted root from the candidate branch, then
create and push the configured proposal branch when remote publication is
available. Local closeout facts remain inputs to the current land and publish
boundaries; actual mutation still requires the command's explicit guarded
options.

This keeps break-glass paths explicit and makes dry-run planning safe by
default.

All public command results use the closed `verdict` union `pass | block | unknown`; the top-level `ok` field is absent. Missing or unverifiable required facts produce `unknown`, conflicts, explicit failures, and warnings produce `block`, and only `verdict = "pass"` authorizes an effect. Domain lifecycle `state = "deferred"` remains distinct from the authorization verdict.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Index](../index.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
