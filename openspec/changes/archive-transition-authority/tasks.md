## 1. Contract and RED

- [x] 1.1 Record the archive recovery, proof remediation, and rebind-routing
  behavior without adding a second lifecycle owner.
- [x] 1.2 Add a regression for an exact archive commit whose Lease and terminal
  Attestation were not advanced.
- [x] 1.3 Add producer-to-consumer coverage for direct derivation and public CLI
  projection.
- [x] 1.4 Add adversarial cases for wrong-parent, semantic-drift, and ambiguous
  archive targets.

## 2. Single-owner implementation

- [x] 2.1 Extract one exact committed-archive fact classifier in the existing
  archive recovery owner and delete its duplicated classification path.
- [x] 2.2 Route rebind derivation to `archive-change` for physical carrier
  relocation and keep non-exact targets fail closed.
- [x] 2.3 Route proof plan failures to the same exact archive command while
  keeping other stale Lease states non-destructive.
- [x] 2.4 Project the derive owner's next action through the shared lane result
  envelope without changing verdict-derived top-level state.

## 3. Verification and closeout

- [x] 3.1 Run the focused archive/rebind/proof regressions and changed-file
  static checks.
- [x] 3.2 Run affected suites, Ruff, format, ty, strict OpenSpec, and repository
  reference closure.
- [x] 3.3 Run the applicable full suite and coverage at the frozen candidate.
- [ ] 3.4 Verify that the implementation is ready for public proof, archive,
  candidate/accepted land, accepted runtime verification, and lane retirement;
  leave those later lifecycle effects to their own exact-head Attestations.
