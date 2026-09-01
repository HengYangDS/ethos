## 1. Regression Contract

- [x] 1.1 Add focused tests proving a current `openspec_validation_failed:spec:<capability>` gap admits only `openspec/specs/<capability>/spec.md`, and observe the tests fail before production code changes.
- [x] 1.2 Add negative tests for unrelated canonical specs, mixed repair and product paths, malformed capability identifiers, and ordinary valid-Commitment scope, and observe the new behavior-specific assertions fail while existing behavior remains characterized.

## 2. Narrow Repair Admission

- [x] 2.1 Derive exact canonical repair paths from the fresh official OpenSpec report without persisting authority, and verify the focused scope tests pass.
- [x] 2.2 Compose canonical repair scope with active-Change attribution while preserving Work Lane, Lease, editor-root, runtime, and path checks, and verify focused prewrite tests pass.
- [x] 2.3 Run the affected admission, OpenSpec lifecycle, and CLI projection test groups and verify no unrelated path is newly admitted.

## 3. Acceptance And Delivery

- [x] 3.1 Validate the complete OpenSpec change strictly and run the repository exact-HEAD quality and test proof.

## Post-Archive Transition Boundary

Official archive, archive-HEAD proof, candidate land, accepted-root closeout,
immutable runtime installation, the original Agentic Workstation repair
prewrite, remote publication, and owned-Lane retirement are separate governed
transitions. They are not pre-archive tasks and MUST NOT be checked or claimed
before their own exact observations prove them.
