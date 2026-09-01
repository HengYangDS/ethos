## 1. Regression Contract

- [x] 1.1 Add focused tests proving a current `openspec_validation_failed:spec:<capability>` gap admits only `openspec/specs/<capability>/spec.md`, and observe the tests fail before production code changes.
- [x] 1.2 Add negative tests for unrelated canonical specs, mixed repair and product paths, malformed capability identifiers, and ordinary valid-Commitment scope, and observe the new behavior-specific assertions fail while existing behavior remains characterized.

## 2. Narrow Repair Admission

- [x] 2.1 Derive exact canonical repair paths from the fresh official OpenSpec report without persisting authority, and verify the focused scope tests pass.
- [x] 2.2 Compose canonical repair scope with active-Change attribution while preserving Work Lane, Lease, editor-root, runtime, and path checks, and verify focused prewrite tests pass.
- [x] 2.3 Run the affected admission, OpenSpec lifecycle, and CLI projection test groups and verify no unrelated path is newly admitted.

## 3. Acceptance And Delivery

- [ ] 3.1 Validate the complete OpenSpec change strictly and run the repository exact-HEAD quality and test proof.
- [ ] 3.2 Archive the completed Change, land through the candidate and accepted transitions, and install a source-independent immutable runtime verified against the accepted commit and tree.
- [ ] 3.3 Re-run the original Agentic Workstation canonical-spec prewrite with the new accepted runtime and verify only the three validator-named spec files are admitted.
- [ ] 3.4 Retire the clean ETHOS work lane and verify its worktree, ref, and Lease are absent while accepted local and remote refs and the installed runtime remain exact.
