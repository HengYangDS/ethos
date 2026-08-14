## Context

The defect family has one cause: lifecycle meaning is reconstructed by several
procedural owners. A Git ref may advance while its Lease does not; a source tree
may declare a role transition that the target checkout cannot see; a package may
emit JSON rejected by its own schema; hook launchers may select different
runtimes; proof and transition code may compare unrelated Commitment digests.
Each local fix strengthens one interpretation while leaving the duplicated
model intact.

The product contract already names the correct semantic roots:

```text
(Commitment, Facts, prior Attestations) -> TransitionPlan -> Attestation
```

This Change makes that equation executable across the complete lifecycle.

## Goals

- One typed operation declaration and one pure reducer.
- One immutable receipt binding observation, authority, plan, effect,
  compensation, and postcondition.
- One exact apply engine and one structured continuation envelope.
- One package manifest binding source, wheel, resources, schemas, CLI, hooks,
  runtime interpreter, and health proof.
- One positive gate graph and one repository-declared commit policy.
- No reusable permission in Commitment and no second workflow state store.
- No compatibility reader, alias, fallback, blacklist, or adopter-specific
  lifecycle engine.

## Non-Goals

- Preserving old state payloads, commands, Campaign carriers, or profile shapes.
- Encoding AIGW, Proxy, Cocogitto, GitLab, GitHub, uv, Go, or any repository's
  branch names in ETHOS.
- Treating SQLite, worktrees, Lease rows, operation logs, runtime locators, or
  provider status as semantic roots.

## Decision 1: One Transaction Algebra

Every mutating public operation is data:

```text
OperationRequest
  + Commitment
  + fresh Facts
  + prior Attestations
  + repository declarations
    -> reduce()
    -> TransitionReceipt
```

`reduce()` is pure. It returns a closed verdict, ordered gaps, exact operation
authority, preconditions, effects, compensations, postconditions, and one
continuation. It performs no I/O and persists no progress.

`apply(receipt)` accepts only the exact immutable receipt. It re-observes every
precondition, executes the declared effects in order, post-observes all declared
postconditions, and issues an Attestation. If an effect is visible but terminal
postconditions are not, the result is `partial`, retains the same receipt, and
names exactly one public resume or compensate action.

## Decision 2: Operation-Bound Authority

Commitment declares intent, subject, scope, invariants, acceptance, risk, and
authority references only. It carries no reusable permission.

Authority is derived for one operation from:

- the selected tracked operation declaration;
- exact actor/holder/maintainer facts;
- exact Commitment and Attestation bindings;
- exact observed refs, trees, Lease generation, worktrees, and provider facts;
- the exact requested effect.

The receipt carries that derivation. Changing any input changes the receipt and
invalidates apply. No authority survives as a general capability for another
operation.

## Decision 3: Resource Coordination Is A Projection

Git refs are the repository substrate. Lease and worktree attachment coordinate
exclusive mutation but do not own lifecycle truth. Their mutations are explicit
effects and their complete terminal relation is a postcondition.

For `refresh-base`, terminal success means all of the following are observed in
one receipt closure:

- the work ref equals the rebased head;
- the candidate assertion remains exact;
- the Lease generation binds the new head/tree/Commitment;
- the worktree is attached to that branch and head;
- the effect Attestation binds the receipt and post-observation.

If Lease advancement or attachment fails after ref CAS, apply compensates the
ref when exact rollback remains valid. Otherwise it returns a typed partial
receipt whose only continuation resumes or compensates that exact transition.

## Decision 4: Commands And Results Are Projections

Cyclopts declarations own names and parameters. A command may collect request
arguments and render results; it may not implement lifecycle policy. `status`,
`plan`, hooks, SDK, JSON, schemas, and docs reduce or project the same contracts.

Every public result uses one closed envelope:

- `verdict`;
- `state` (`ready`, `applied`, `partial`, `blocked`, `done`);
- `required_gaps`;
- receipt and Attestation identities when present;
- one `next_action` or one explicit user decision;
- bounded diagnostics with no traceback.

## Decision 5: Package And Hook Identity

The immutable package manifest binds accepted source commit/tree, wheel and
entrypoint bytes, dependency lock, bundled schemas/resources, CLI help digest,
OpenSpec runtime, interpreter strategy, hook launchers, and black-box receipts.
Activation selects exactly one healthy runtime only after final-path tests pass.
All linked worktrees and all declared hooks converge atomically; obsolete broken
runtimes retire only after active-runtime and launcher readback proof.

Runtime launchers may not embed a temporary staging path or Homebrew patch-level
interpreter path. A missing interpreter triggers package-owned repair before
activation rather than leaving a half-installed runtime current.

## Decision 6: Repository Declarations, Not Repository Engines

Profiles declare policy facts:

- branch roles and role-transition edges;
- commit-message argv, placeholder, and locked inputs;
- gate graph, required execution contexts, SSOT and derived carriers;
- actor/signature/trust policies and provider identity profiles;
- provider projection topology and release policy.

ETHOS compiles and executes those declarations. Adopters do not provide wrapper
scripts, second hook owners, history-rewrite engines, lifecycle commands, or
provider-specific orchestration engines.

## Decision 7: One Change, One Task Graph

`openspec/changes/model-promotion/tasks.md` is the only progress authority for
this promotion. The terminal product plan links to it and contains no Campaign,
delivery queue, compatibility roadmap, or second checklist. Work may land in
small commits, but all commits advance this one dependency graph and one Change.

## Vertical Migration Order

1. Freeze the new contracts with reducer property tests.
2. Migrate `refresh-base` end to end and delete its command-local orchestration.
3. Migrate land/closeout and source-to-target role transitions.
4. Migrate Lease recovery, rebind, retirement, and history replacement.
5. Migrate hooks, package runtime selection, and state cutover.
6. Migrate proof execution and required-gate completeness.
7. Migrate provider-native proposal projection and independent ingestion.
8. Delete Campaign, reusable permissions, duplicate effect admission, old
   schemas, compatibility code, and stale documentation.

## Verification

- Property tests prove reducer determinism, input sensitivity, closed verdicts,
  exact authority, compensation, and resumability.
- Mutation tests interrupt every effect boundary and prove either complete
  postconditions or one exact partial continuation.
- Package-only black boxes run CLI, schemas, hooks, OpenSpec, migration, proof,
  land, transition, retire, and publish without source checkout.
- Real read-only AIGW and Proxy probes prove declarations and current facts can
  compile. Their owners alone apply mutations.
- Final acceptance requires exact-HEAD full proof, OpenSpec archive, post-archive
  proof, signed land/closeout, accepted runtime activation, and safe runtime
  housekeeping.
