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
release_root -> accepted_root -> candidate -> work_lane. A `proposal/*` ref is a governed remote review projection, not a local authoring role.
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
The standard Work Lane lifecycle starts from an official OpenSpec Change and a
fresh Git observation. ETHOS compiles the official projection into the
three-field Commitment and records only the four-field Lease relation. It then
derives exact source and target ref intent; missing, ambiguous, stale, or
conflicting facts block before any ref, worktree, or SQLite effect. `ethos lane
refresh-base` replays a stale lane onto the configured candidate
branch. It creates ordinary new local commits when Git requires them; it never
reconstructs an existing product object merely to change identity or signature.
History-preserving integration uses `refresh-base --strategy merge`; its
operation-aware preview, continue and preserved abort are described in the
[command reference](../reference/command-plane.md#native-merge-continuation).
Native parent provenance selects lane intent without consuming another Change's
progress. A pending merge is not a dirty-rebase recovery instruction.
`ethos land` advances the configured candidate branch, and `ethos lane retire landed`
removes only an explicitly named clean landed Work Lane at the expected Work
Lane HEAD. `ethos lane retire superseded` may retire one clean ownerless source
whose exact HEAD is already absorbed by the current owned lane; the transaction
preserves the integration ref and current Lease. Prewrite, TransitionPlan,
proof, ref advance, handoff, closeout, retirement, and status consume the same
Lease observation plus fresh Git facts. Cross-host source revocation is likewise
an exact live-Lease CAS: a missing Lease blocks and never masquerades as replay.

`ethos lane archive-change` closes the lifecycle edge that cannot be split
between an external archive process and a later Git commit. It requires the
same-holder Lease and proof for the pre-archive HEAD, runs official OpenSpec
from the package-bound supply, admits only its exact rename/spec delta, commits through ordinary
hooks, and attests the post-state. The archived HEAD remains plan/proof/land
capable because acceptance is compiled from its exact official projection.
Unbound Work Lane refs are observations only. Status preserves their exact ref,
HEAD, Lease observation, and accepted-relation facts, but no lifecycle
command deletes them.
Unknown, dirty, unbound, or owner-uncertain state remains observe-only until a
public transition can derive an exact safe effect from current facts. Raw Git
worktree creation can exist as a repository fact, but it is not authority.

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
second truth store. Repository-family execution instead selects one immutable
package runtime through `<git-common-dir>/ethos/runtime/CURRENT`. Hook launchers
and executable remediation resolve that same selector; historical launcher
bytes and ambient `PATH` are not alternate authorities. Runtime activation
validates the candidate before selection, post-observes the shared binding, and
restores the exact prior selector plus Git configuration on failure.
For a source checkout, `uv.lock` owns dependency resolution while that exact
checkout's root lock-current `.venv` supplies build tooling and installed
dependency bytes; an older invoking runtime only coordinates activation.
Installation verifies the complete target environment before a non-isolated
wheel build, copies it, strictly prunes the copy to the hash-bound production
closure, and installs the exact wheel. The uv cache remains a disposable
acceleration layer, never a prerequisite or authority. A selected package-only
runtime derives successors from its validated production closure and the exact
wheel in the same Git-common `ethos/packages/<sha256>/` store. An
installer-created `direct_url.json` may record an installation source path, but that path
is not runtime authority and need not remain present after relocation.

Its mode is `maintainer_break_glass_local`: a current ETHOS
runner is allowed to execute the protected closeout with an explicit
`--root <accepted-root>`, while remote push remains `deferred` and the candidate
worktree is audited and proven before accepted-root movement.

A changed gate obligation requires explicit acceptance of the exact candidate,
not automatic enrollment in an external verifier. The control-replacement report
binds both commits, trees, control digests, the candidate's executed Attestation
and changed obligations. Closeout of that replacement requires `--authorize`,
the exact accepted `--expect-head` and explicit `--candidate-head`; fresh effect
checks and CAS remain mandatory. The report and proof do not grant authority.

Independent verification follows the stricter policy read from the two exact
committed objects. A candidate cannot disable a required predecessor verifier.
Execution-identity changes are review information, not proof of weakening or
equivalence, and cannot turn disabled or optional policy into required policy.

[Independent verification adoption](../governance/independent-verification-adoption.md)
owns the provider, protected receipt store and recovery boundary. Control
replacement and publication consume the same configured-evidence owner before
offering an effect. Provider setup does not authorize repository changes, and
a local re-execution is not an independent identity claim.

If the accepted root and candidate branch already resolve to the same HEAD,
closeout is current rather than ready-to-mutate. `ethos land --closeout --json`
reports `state = "accepted_current"`, `closeout_bootstrap.state = "current"`,
and `ethos publish` as the next action. Apply mode is a no-op in that state: it
still requires `--authorize` and `--expect-head` as mutation-safety intent, but
it does not require a new candidate proof because no new candidate head is being
promoted.

`ethos publish --json` remains the local readiness boundary. Remote projection
has one explicit entry point: `ethos publish --ref <full-ref> --probe-remote
--expect-head <head> --json`. The full ref is resolved through the positive ref
topology. All targets share one object/request/executor contract; the target
role selects proof obligations. Review requires source trust and introduced-range
policy but no fabricated Commitment or product proof. Accepted branches, release
branches and annotated release tags retain their stronger proof and closeout.
The dry-run observes every declared peer with live `ls-remote`, compiles one
content-addressed request, and performs no push. The guarded apply form consumes
that request internally; the explicit receipt form provides restartable
execution. Both recheck the exact local object and signature trust, request
digest, repository common directory, push admission, and every target ref
before the first effect. Immediately before each peer transaction, they recheck
source trust, required proof, declared targets and that peer's exact current
refs. An earlier matching peer observation cannot stand in for this recheck.

Each declared peer push uses provider-local exact CAS. Git cannot make multiple
providers one atomic transaction, so ETHOS never claims cross-provider
atomicity. If a later peer fails, the terminal Attestation names applied,
failed, and pending peers; rerunning the same public receipt path converges peers
that still match without rewriting them. Unavailable intent or peer observations
remain UNKNOWN; a known policy violation still blocks independently. Hosted CI remains a subsequent
independent evidence state rather than an implication of push success.

Local readiness carries no publication effect or implicit target. The caller
selects one admitted full ref explicitly. In local-first mode, candidate closes
into accepted `dev`/`main` before those exact accepted objects are projected. In
proposal/MR mode, a selected trusted object, including an unfinished Change,
is projected to an explicit `refs/heads/proposal/*` target. Candidate and Work
Lane refs remain local-only; the checkout role does not decide review readiness.
Actual mutation still requires the command's guarded options.

Detached CI calls `ethos hook ref-update` with explicit target, proposed and
previous objects and remote/baseline coordinates. The shared admission owner
reads exact Git trees and the existing commit-range validator; it does not
consult a host Lease or issue proof. The command reports the boundary, reason,
coordinates and one read-only diagnostic. Prior target policy remains the floor
until an exact accepted closeout supplies an already-accepted policy. CLI,
pre-push and replay do not maintain their own interpretation of these roles.

This keeps break-glass paths explicit and makes dry-run planning safe by
default.

All public command results use the closed `verdict` union `pass | block | unknown`; the top-level `ok` field is absent. Missing or unverifiable required facts produce `unknown`, conflicts, explicit failures, and warnings produce `block`, and only `verdict = "pass"` authorizes an effect. Domain lifecycle `state = "deferred"` remains distinct from the authorization verdict.

Status: see front matter.

Purpose: explain the repository truth represented by this ETHOS document.

See also: [Documentation Root](../README.md), [Command Plane](../reference/command-plane.md), and [Glossary](../reference/glossary.md).
