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

- [x] 3.1 Run strict OpenSpec, claims, parity, and executed HEAD-bound proof at 9f253b76242406f908f8b0d4a7a0baebb1b229f4 (19 gates; cf256557307df25f8d2d2783be402e312d238c50527faf28f53685f179e0ff7f).
- [x] 3.2 Archive the authority carrier and bind land plus accepted local closeout as the required promotion path.
- [x] 3.3 Bind one native clear plus receipt verification as the sole post-closeout effect; then retire this carrier through the ordinary landed lifecycle.

## Post-archive transition boundary

After this carrier is accepted locally, native clear may affect only the exact
manifest-bound package. A changed package, digest, Chronicle, or receipt blocks
the effect. The original decision and receipt remain durable; this carrier is
temporary and must be retired after the clear receipt is verified.
