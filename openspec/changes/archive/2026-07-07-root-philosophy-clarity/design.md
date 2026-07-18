## Context

The Product Design Contract owns the canonical root text. OpenSpec owns this
change carrier. `system/axioms.md` is a derived machine-adjacent review aid and
must stay subordinate to product docs.

## Design

`问道` remains visible only at canonical product and kernel explanation layers.
The active repository no longer treats philosophy labels as named subsystems. `system/axioms.md`
contains short engineering invariants that tests and code review can cite without
copying the verse or turning it into a module map.

The kernel model says the chain is an engineering compression compatible with the
root constraint. It does not claim direct line-by-line derivation. Active code,
configuration, hooks, and system TOML comments use concrete engineering language:
proof-binding invariant, parsimony invariant, boundary invariant, and similar
plain phrases.

## Alternatives

Keeping the old derived-file name is shorter in diff but preserves the false center.
Using `root-principles.md` is clearer but too long and still sounds like a
parallel root. `axioms.md` is short, precise, and subordinate.

## Proof Strategy

- Architecture tests check that `system/axioms.md` does not duplicate the root
  verse and that low-level active surfaces do not cite philosophical labels.
- Product design tests check that the Product Design Contract remains the root
  source and that the kernel model describes the boundary correctly.
- `ethos openspec --change root-philosophy-clarity --json` validates the carrier.
- Focused pytest and HEAD-bound `ethos prove --execute` provide closeout evidence.
