# Design

## Context

See [proposal.md](proposal.md). `knowledge-currency` split the repository-governance corrections by area, because one delta file must stay within the repository paradigm's 512-line Markdown ceiling (its design, "Spec deltas"). This Change carries the Work Lane coordination area: 11 requirements.

Constraints:

- **Requirement length.** OpenSpec 1.15.0 strict validation fails a requirement whose text exceeds 500 characters, and only the archive simulation sees it.
- **Scenario names.** OpenSpec matches scenarios by name, so a MODIFIED block cannot drop or rename one.
- **Concurrency.** The product lane's `promote-by-identity` and `one-proof-per-change` own other repository-governance ranges; this Change touches none of them.

## Goals / Non-Goals

**Goals:**

- The 11 requirements state the current Lease, handoff, refresh, retirement, publication and status behavior, each claim verified against the code at the Change's base.

**Non-Goals:**

- Behavior changes. Where code and requirement disagree, the requirement follows the code; a product defect found on the way goes to the product lane.
- `lane-reconciler` (batch 3) later reduces the lane commands to the TP's transitions and rewrites these requirements again; this Change only makes them true now.

## Decisions

### Titles kept where true

A requirement whose title and scenario names stay true keeps them and restates its full text with the current mechanism (5). A requirement with a title or scenario that names a removed mechanism is REMOVED and ADDED under a name that states the current obligation (6), because OpenSpec matches scenarios by name:

| Removed                                                                      | Added                                                                                 | False title or scenario                                                                |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Context-bound mutation admission                                             | Mutation admission is bound to explicit repository context                            | refresh-base resolves parity projection-only conflicts as stale projection             |
| Work Lane Lifecycle Resolution                                               | Work Lane lifecycle resolves from current facts                                       | lane handoff is recorded as Chronicle resolution                                       |
| Work Lane refresh success is ancestry-bound                                  | Work Lane base refresh reports success only on candidate ancestry                     | parity-projection recovery preserves the same success condition                        |
| Resolution Decisions and Receipts are semantically disjoint                  | Handoff contracts reject coercion and ambiguous object IDs                            | A resolution effect completes                                                          |
| Authorized Work Lane cohort closeout is exact and evidence-bound             | Work Lane cohort retirement binds each exact target                                   | Zero missing behavior selects preservation closeout, not integration                   |
| Dirty and unbound Work Lane content is preserved before destructive closeout | Dirty and unbound Work Lane content is retired only through an exact reviewed receipt | the title itself: reviewed content is hashed into a receipt and removed, not preserved |

The lifecycle replacement drops the break-glass scenario. It names a predeclared break-glass Commitment and an accepted reconciliation that no code implements: closeout knows only the `maintainer_break_glass_local` bootstrap mode (`src/ethos/domain/land/closeout.py`). The PDC's bounded maintainer recovery owns that path, and a Commitment is transient, so it cannot be predeclared.

### Verification

A read-only review checked every claim of the planned text against the code at `ad9108d70`; fbee0c spot-checked each contradiction. The review's table, with a file and line for each claim, is this Change's evidence (`build/runtime/work/fbee0c-session/coordination-spec-currency/audits/V1-coordination-verification.md`). It changed the plan as follows:

- **Retirement preserves no content.** `ethos lane retire abandon --review-content` checks content against a hash manifest and removes it; only the receipt survives. Two requirements are therefore replaced (above), and the cohort convergence scenarios say "reviewed into that receipt".
- **Exceptional judgment is a receipt or an accepted takeover Attestation.** Irreversible retirement consumes an exact authorized receipt; only takeover consumes an accepted `lane-resolution:takeover` Attestation. No decision Attestation or Commitment input exists for retirement.
- **Handoff emits an effect Attestation** (`effect:handoff-package`), not a decision Attestation.
- **The ownerless resolver is gone** (`ed18713a0`); a clean diverged lane without a valid Lease retires through reviewed abandonment.
- **Publication** persists one exact dry-run TransitionPlan and applies one atomic push with an exact lease per protected ref; a proposal ref is deleted only after the accepted peer branch contains its tip or accepted replacement and its review is not open.
- **One migration path.** "Runtime activation" and "hook installation" name one code path, so the schema requirement names it once: Git-common hook runtime activation.

One accepted statement stays although the code does not meet it. "Sanctioned Work Lane replay binds its named ref" says a missing named ref fails closed; the code binds the detached HEAD instead (`src/ethos/adapters/admission/current/authority.py`, `binding_head or current_head`). The requirement keeps the intended fail-closed behavior, and the defect went to the product lane on 2026-10-28.

## Risks / Trade-offs

- [The base moves before archive] → The archive simulation and strict validation run on the lane's head after any refresh.
- [A claim verified today changes before landing] → The product lane's open Changes do not touch these requirements' code paths; the verification table names each path.
