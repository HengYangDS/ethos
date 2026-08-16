# Tasks

- [x] **1. Record the exact repair coordinates.** Record the baseline,
  defective commit, and pre-repair accepted HEAD.
- [x] **2. Bind the public recovery authority.** Bind the repair to the
  accepted public identity-repair capability.
- [x] **3. Define bounded acceptance evidence.** Define payload preservation,
  exact-CAS, trust, and convergence evidence.
- [ ] **4. Restore receipt dry-run parity.** Reproduce the gapless blocking
  verdict, add the focused public regression, and project pass/ready only when
  the existing receipt validator finds no gap.

## Proof mapping

| Obligation | Task | Evidence |
| --- | --- | --- |
| `command-plane:Identity repair uses exact public authority and CAS` | 1 | `receipt:identity-repair-derive-apply` |
| `command-plane:Identity repair preserves commit payloads` | 2 | `receipt:identity-repair-commit-mapping` |
| `quality:Repaired suffix and product state are proven` | 3 | `proof:trusted-suffix-exact-head-closeout` |
| `command-plane:Identity repair receipt dry-run authorizes exact apply` | 4 | `tests:identity-repair-dry-run-parity` |

The proof, derive, apply, signature verification, archive, land, closeout,
retirement, and runtime rebuild are post-task governed effects. Each must emit
its own terminal receipt; task completion does not claim those effects occurred.
