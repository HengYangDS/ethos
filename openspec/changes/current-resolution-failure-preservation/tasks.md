## 1. Contract And RED

- [x] 1.1 Validate the official Change strictly and verify that the modified command-plane requirement expresses failure preservation without adding another authority owner.
- [x] 1.2 Move the existing current-authority cross-surface regression to its semantic test owner, include `prove`, and observe the expected failure when one fresh authority gap is projected differently.
- [x] 1.3 Add a focused regression proving that a non-passing `CurrentResolution` prevents proof-plan construction and preserves verdict, ordered gaps, next action, and user-decision state unchanged.
- [x] 1.4 Add focused regressions proving that a passing frozen resolution is the only authority input to proof-plan compilation, candidate/accepted repository proof remains valid with no Commitment, and Attestation issuance still rejects live Lease-generation or actor drift.

## 2. Replacement And Deletion

- [x] 2.1 Make proof terminate on a non-passing current resolution while preserving proof-specific summaries only as non-authorizing presentation.
- [x] 2.2 Stop swallowing unexpected current-resolution errors and remove proof-local gap-prefix recovery mapping and its obsolete expectations.
- [x] 2.3 Make proof-plan compilation consume the frozen resolution without rereading Lease or actor state, while preserving issuance-time exact live rechecks and reporting drift from that owner.

## 3. Closure

- [x] 3.1 Run focused current-resolution, public-surface, proof, result-contract, and command-plane tests; verify repository-wide references contain no superseded proof-local recovery mapper.
- [x] 3.2 Run strict OpenSpec validation, formatting, lint, typing, import-boundary, module-layout, and affected repository gates with no warnings or hidden fallback.

## Lifecycle Transition Boundary

After every task above is complete, create the signed implementation commit and
run exact-HEAD full proof. Then archive the official Change, reprove the archive
commit, advance candidate and accepted refs through exact CAS, read back the new
immutable package-only runtime and OpenSpec identity, and retire this Work Lane.
These transitions are required completion evidence and are not satisfied by the
pre-commit checklist alone.
