## 1. Retire the competing state owner

- [x] 1.1 Delete the checkout-local state adapter, migration command, migration
  guards, schema fallback, and migration-only tests; verify retired-symbol search
  finds no active implementation reference.
- [x] 1.2 Route Lease, lifecycle, status, hook admission, and proof artifacts
  through the Git-common state owner; verify affected modules import and focused
  state/lifecycle tests pass.

## 2. Close repository projections

- [x] 2.1 Remove `.ethos/state/**` from tracked ignore rules, generated-artifact
  policy, product boundaries, repository declarations, documentation, fixtures,
  and scaffolding; verify repository-wide closure leaves only intentional
  deletion scope and retired-command detection data.
- [x] 2.2 Preserve public fail-closed proof diagnostics outside a Git repository
  and make tests create tracked `.ethos/` parents explicitly; verify the affected
  proof and hook regression slice passes.

## 3. Verify the bounded change

- [x] 3.1 Run formatter and Ruff over source and tests with no findings.
- [x] 3.2 Run the affected state, lane, hook, CLI, proof, and policy test slice and
  verify all 142 tests pass.

Post-checklist strict OpenSpec validation, complete changed/full proof, archive,
land, closeout, and historical-residue disposition remain public lifecycle
effects. They are not checked before they occur and do not require another
progress owner.
