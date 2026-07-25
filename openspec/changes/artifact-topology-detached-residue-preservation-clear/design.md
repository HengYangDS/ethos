## Context

Native `preserve-retire` correctly retained the dirty source state before
removing its lane. The durable decision and completion receipt remain audit
evidence. Only the exact package is removable, and only after its manifest and
accepted replacement basis are bound by a separate accepted carrier.

## Design

Use a fresh owned Work Lane with one Claim, Chronicle, plan, and OpenSpec delta.
The Chronicle selects `lane_resolution/clear-preservation` for one decision id
and manifest. Native clear rechecks inventory and manifest bytes, removes only
the package, retains the original decision and completion receipt, and emits a
clear receipt. The temporary carrier is then retired normally.

## Alternatives

- Retain indefinitely: rejected because the payload has no unique current
  behavior and would remain unowned recovery residue.
- Remove manually: rejected because it bypasses manifest CAS, clear receipt,
  and the irreversible native control surface.
- Clear a batch: rejected because this carrier has evidence for one package
  only.

## Proof Strategy

Validate package integrity, strict OpenSpec, Claim digest, docs, focused
behavior, generic parity, and executed HEAD-bound proof. Archive, land, and
close out locally before native clear; then check inventory, retained receipts,
and exact package absence before retiring this carrier.
