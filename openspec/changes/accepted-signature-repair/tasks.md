# Tasks

- [x] Record the exact baseline, defective commit, and pre-repair accepted HEAD.
- [x] Bind the recovery to the accepted public identity-repair capability.
- [x] Define payload preservation, exact-CAS, trust, and convergence evidence.

## Proof mapping

| Obligation | Evidence |
| --- | --- |
| Exact authority and CAS | identity-repair derive/apply receipts |
| Payload preservation | receipt commit mapping and command admission |
| Trusted suffix | `git verify-commit` for every commit after the baseline |
| Rewritten product correctness | post-repair exact-HEAD full proof |
| Accepted closure | archive, land, closeout, retire, runtime receipts |

The proof, derive, apply, signature verification, archive, land, closeout,
retirement, and runtime rebuild are post-task governed effects. Each must emit
its own terminal receipt; task completion does not claim those effects occurred.
