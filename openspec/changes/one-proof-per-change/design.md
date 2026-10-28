# Design

## Context

See [proposal.md](proposal.md). Design revision 5.1 decides D1, option A: archive is a lane-local effect that stays compensable until landing, and landing requires the passing proof of the exact archived head (`build/runtime/work/architecture-realization/product-architecture.md`, "One proof per Change"; `design.md`, D1).

| Case                                       | Before: proof, archive, proof           | After: archive, proof                              |
| ------------------------------------------ | --------------------------------------- | -------------------------------------------------- |
| Success                                    | 2 proofs                                | 1 proof                                            |
| The proof finds a code defect              | proof, fix, proof, archive, proof: 3    | archive, proof, compensate, fix, archive, proof: 2 |
| The archive changes an input a check reads | proof, archive, proof, repair, proof: 3 | archive, proof, compensate or repair, proof: 2     |

Constraints:

- **Budget.** `python_product` is 69,976 of 70,000 on `dev`. The route-out rule applies: the Change deletes at least as much as it adds.
- **Concurrency.** The product lane runs `surface-pruning` and `shared-quality-obligations`. Neither edits the archive command, `landing.py`, `runner-and-mutation.md` or the archive passage of `command-plane.md`. `shared-quality-obligations` also deltas repository-governance, for another requirement; whichever lands second refreshes before it archives.
- **Predecessor.** Hooks, closeout and publication run the installed runtime. The archive command runs from the lane's own source, so this Change can use its own route.

## Goals / Non-Goals

**Goals:**

- One complete proof per source Change, of the exact head that lands.
- A failed archived-head proof returns the lane to its exact pre-archive head through one attested effect.

**Non-Goals:**

- Changing landing, closeout or proof admission. They already require the exact archived head's proof.
- Delivery-inclusive Changes, which land with an active Change and keep proving it. Their archive simulation (repository-governance "Proof requires an archivable Change") is unchanged.
- Reusing gate results between proofs, which belongs to `verification-throughput` and `gate-input-reuse`.

## Decisions

### 1. Archive admits an unproved head

`_archive_coordinate_gaps` keeps the Work Lane role and exact-head checks and drops `proof_gaps`. Everything that protects the archive itself stays: the Lease and actor, the completed Change, the commit subject, the collision check, the clean tree, and native strict validation of the actual postimage before the commit. After the ref update, `complete_archive` already checks the archived head's proof. Its report is now named `pending_verification`, with the proof of that head as its continuation, and it still blocks: the effect is committed, and the Change is not complete until the proof passes.

### 2. Compensation is one attested compare-and-swap

`lane archive-change --compensate --expect-head <archived-head>` (`archive/compensation.py`):

- **Admission.** The lane checks of every lifecycle transition (`work_lane_transition_gaps`): a valid Lease held by the actor, the Work Lane role, the exact head and a clean tree.
- **Selection.** The head must be an attested archive of the named Change at distance zero. `attested_archive_transition` resolves the archive effect directly or through a base refresh, so a compensation after a refresh works too. The head must not be contained in the candidate branch; a landed archive is no longer lane-local.
- **Effect.** One Git effect moves the lane ref from the archive commit to its parent. It is compiled with the archived Commitment, bound to the current Lease generation and to the archive authority, and attested by the executor. `compensate_git_worktree` then restores the index and worktree to the parent.
- **Recovery.** If a run stops after the ref update, repeating the command finds the attested compensation whose expected head is the archive commit. It restores the index and worktree only when they still hold exactly the archived tree, or are already restored.

The old archive Attestation stays in the set. It no longer resolves for the lane: its archive commit is not an ancestor of the restored head, and no refresh edge leads from it.

Alternatives rejected:

- **Fixing forward on top of the archive.** After archive the write scope is the archive effect's paths. Widening it would give an archived Change a second, mutable life.
- **Reverting the archive with an ordinary commit.** A revert keeps both commits in the landed history and is not an effect that the archive authority understands.
- **The detached carrier of option B.** It keeps two proofs' worth of machinery and four conditions; D1 drops it.

### 3. The execution carrier is retired

`ProofExecutionCarrier` and `prove --execution-root` proved a pre-archive head while a staged archive kept the lane dirty. Without the precondition, `archive-change` finalizes the staged archive and the archived head is proved in the clean lane. The module, its option, its threading through proof planning, issuance and persistence, and its two requirements are removed. Source correspondence during a proof stays with quality's "Exact commit proof binds observed execution source", and the current policy floor with "Current-policy proof coexists with immutable superseded proofs".

### 4. Documents

`runner-and-mutation.md` states the route and compensation, names the runner that exists (`LocalGateRunner`), and drops the paragraph about copying the proof record into the candidate worktree: proof Attestations live in the Git common directory, so every worktree reads the same proof (removed in `7ec70e37a`). `command-plane.md`, the release guide and the governance Skill map state the same route.

### Spec delta

repository-governance:

- MODIFIED "Archive completion requires exact postimage quality": archive needs no pre-archive proof; its scenario for an archive that changes a checked input reports pending verification.
- MODIFIED "Exact proof query selects intent without weakening evidence": explicit archive archives only the named Change, whose archived head needs its own proof.
- ADDED "An unlanded archive returns to its pre-archive head".
- REMOVED "Proof execution carrier is not proof authority" and "Carrier proof preserves independent admission boundaries".

## Risks / Trade-offs

- [More archives of broken code] → An archive is lane-local until it lands, and landing still needs the passing proof of the exact archived head. Compensation is one command.
- [Compensation discards a landed archive] → It refuses when the archive commit is contained in the candidate branch.
- [Compensation discards the author's later work] → It requires a clean tree at the exact archive commit, and resumes only over exactly the archived tree.
- [Adopters keep the old order] → An adopter's installed runtime still requires a pre-archive proof until a release carries this Change, so the Change goes into the next release.
