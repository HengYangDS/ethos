## Context

The Ruff policy owner and ratchet both suppress `EM102`, while the only
findings occur in `ProofRun.__post_init__` validation.

## Design

Each dynamic validation message is assigned before `ValueError` is raised. The
observable message and validation semantics stay unchanged. With no remaining
diagnostic, `EM102` leaves both exception carriers and is evaluated by the
existing canonical Ruff owner; no secondary policy or compatibility path is
introduced. The same binding removes two `TRY003` findings, so its exact ratchet
shrinks from 10 to 8. This records a measured debt reduction; it does not claim
that `TRY003` itself has been eliminated.

## Alternatives

1. Keep a zero ratchet baseline: rejected because the rule remains suppressed.
2. Disable the rule locally: rejected because it hides a general policy debt.
3. Bind messages before raising: selected because it satisfies the rule without
   changing the public validation contract.

## Proof Strategy

Run focused evidence-model and quality-policy tests, a tracked-corpus `EM102`
probe, the canonical lint owner, strict OpenSpec validation, and current-HEAD
proof before integration.
