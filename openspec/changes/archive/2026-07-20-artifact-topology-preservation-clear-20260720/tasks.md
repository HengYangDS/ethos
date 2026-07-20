## 1. Exact retention boundary

- [x] 1.1 Bind the decision id, package path, manifest digest, patch digest, and
  immutable prior receipt.
- [x] 1.2 Prove the retained patch is only stale parity metadata and adds no
  product behavior beyond the accepted local proof.

## 2. Clearance authority

- [x] 2.1 Add a single-package Claim, Chronicle, plan, and OpenSpec delta.
- [x] 2.2 Require native `lane_resolution/clear-preservation`, manifest CAS,
  break-glass, and irreversible confirmation; retain the decision and receipt.

## 3. Validation and lifecycle

- [ ] 3.1 Run strict OpenSpec, claims, parity, and executed HEAD-bound proof.
- [ ] 3.2 Archive this authority carrier, land, and complete accepted local
  closeout.
- [ ] 3.3 Execute and verify the one native clear; retire this carrier.

## Post-archive transition boundary

After this carrier is accepted locally, native clear may affect only the exact
manifest-bound package. A changed package, digest, Chronicle, or receipt blocks
the effect. The original decision and receipt remain durable; this carrier is
temporary and must be retired after the clear receipt is verified.
