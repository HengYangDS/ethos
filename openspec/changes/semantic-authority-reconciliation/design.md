## Context

See `proposal.md` for motivation. A frozen source audit reduced the recovered
feedback to twenty current terminal invariants and distinguished them from
obsolete carrier designs and unverified implementation claims. The present
product contract already owns the semantic kernel, while the terminal plan owns
convergence order; neither role requires another ledger, registry, or roadmap.

## Goals / Non-Goals

**Goals:**

- Make the product contract complete enough to decide whether a proposed
  mechanism belongs in ETHOS and which authority owns it.
- Make the terminal plan independently carry the remaining dependency order,
  acceptance boundaries, re-planning triggers, and final exit condition.
- Preserve product capabilities such as Change dependency inquiry and
  hypothesis/experiment loops without restoring their rejected persistent
  carriers.
- Separate terminal requirements from current implementation status so that a
  documented invariant is never mistaken for completed code or hosted proof.

**Non-Goals:**

- No product-code, schema, test, provider, runtime, remote, adopter, or foreign
  Work Lane mutation.
- No repository-wide physical cleanup in this Change.
- No restoration of `commitment.toml`, predecessor/successor fields, experiment
  DSLs, conversation ledgers, feedback registries, or parallel roadmaps.
- No claim that GitHub, GitLab, signatures, CI, releases, adopters, or historical
  evidence are currently converged.

## Decisions

### Keep exactly two durable design owners

`docs/governance/product-design-contract.md` owns product meaning and terminal
invariants. `docs/plans/terminal-governance-product-design.md` owns the ordered
route from the current implementation to that contract, including acceptance
and exit conditions. Official OpenSpec artifacts own only this bounded change's
intent and task progress.

Alternative rejected: a new semantic ledger or feedback registry. It would
become a third authority and repeat the failure this Change is intended to
remove.

### Preserve capabilities while deleting accidental entities

Change dependency inquiry is derived from current official dependencies, Git
ancestry, and selected Attestations. Hypotheses and experiment procedures live
in official OpenSpec design and tasks; execution uses an owned Work Lane, and
observations or conclusions become Attestations only when they must survive.
Neither capability requires predecessor/successor fields or an experiment
schema.

Alternative rejected: equating deletion of an invalid carrier with deletion of
the product capability it tried to model.

### State topology and lifecycle as positive invariants

The contract will define authoring, review, integration, release, remote,
proof, runtime, recovery, documentation, evidence, and temporary-resource
boundaries directly. It will not preserve an incident catalog or negative
exception list. The terminal plan will then order bounded successor Changes by
dependency and require each to delete superseded owners before the next
overlapping Change starts.

Alternative rejected: patching each observed adopter failure independently.
Those failures are evidence for shared authority boundaries, not separate
product models.

### Modify only the existing design-authority requirement

The Change modifies the existing `repository-governance` capability because the
repository audit must distinguish a complete current design authority from a
document that delegates current work to obsolete history. It does not duplicate
each terminal invariant into separate capability deltas: those behavioral
requirements already belong to their existing capability owners, while this
delta governs the completeness and honesty of the two canonical design
documents.

Later implementation Changes must modify their relevant capability specs and
executable owners. This Change cannot stand in for those proofs.

## Risks / Trade-offs

- **A complete contract may be mistaken for completed implementation.** → The
  terminal plan names every remaining implementation batch and the completion
  boundary forbids that inference.
- **Detailed design can duplicate lower-level rules.** → The contract states
  semantic invariants and links physical module-layout enforcement to its
  existing rule owner instead of copying it.
- **The plan can become another backlog.** → It carries only dependency order,
  acceptance, and exit conditions; task progress stays in the one active
  official OpenSpec Change for each bounded implementation atom.
- **Historical feedback may contain conflicting advice.** → Only the adjudicated
  terminal invariant is retained; obsolete and rejected carriers are named only
  when needed to prevent their reintroduction.

## Migration Plan

1. Reconcile the product contract with the accepted terminal invariants.
2. Replace stale archived-task delegation in the terminal plan with its own
   current dependency order and acceptance boundaries.
3. Validate the official OpenSpec Change and the repository-selected docs,
   links, semantic-closure, and changed-scope gates.
4. Archive this Change only after both documents are internally consistent and
   no implementation or hosted-state claim has been introduced.

Rollback is deletion of this unaccepted Work Lane Change or exact Git revert
after acceptance. No runtime or adopter migration is part of this Change.
