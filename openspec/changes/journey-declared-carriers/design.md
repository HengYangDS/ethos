# Design

## Context

See [proposal.md](proposal.md). `load_repository_paradigm()` in
`src/ethos/contracts/paradigm/declaration.py` returns the declaration that product code builds every
carrier name from: `release.changelog` and `binding.path(role)` among them. The owned-literals test
lets delivery acceptance under `tools/` keep a falling number of restatements while its owners
migrate them.

## Goals / Non-Goals

**Goals:**

- The tools' restatements fall below the ratchet, and the ratchet records the new count.

**Non-Goals:**

- Migrating the other restatements of the delivery acceptance, which keep their owners.

## Decisions

- **Read the names from the declaration.** The journey qualifies ETHOS's own release, and the
  fixture adopter follows the default paradigm, so both names come from the same declaration that
  the product reads.
- **Lower the ratchet in the same commit.** The count only falls; leaving it at 19 would let a later
  restatement return unnoticed.

## Risks / Trade-offs

- [The full proof ran the architecture tests that the lane's local checks had skipped] → The lane's
  checks before an archive now run every architecture test and the module-layout provider.
