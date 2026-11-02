# Tasks

## 1. Landing authority

- [x] 1.1 Bind the landing authority to the Change that the admitted proof carries. Done when a lane
      that archived two Changes and was proved with the first lands without a Change selection, its
      candidate effect binds the first Change, and a carried encoding that is not admissible at the
      head still refuses with the candidate branch unchanged.
      (`tests/unit/cli/land/test_proof_authority.py`: the first case refused
      `proof_attestation_authority_binding_mismatch` before the fix and both pass after it; the 12
      landing, closeout and proof admission modules pass, 194 cases.)
