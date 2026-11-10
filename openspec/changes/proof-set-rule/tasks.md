# Tasks

## 1. Rule

- [ ] 1.1 Plant a narrower `default` whose closure holds a networked gate, and one that holds a
      package gate, together with a `default` equal to `full` that holds a networked gate. Done
      when the two narrower cases fail on the current validator and the equal case passes.
- [ ] 1.2 Enforce the rule in `_validate_proof_sets`. Done when the planted cases refuse with the
      new message, the equal case passes and ETHOS's registry loads.
- [ ] 1.3 Record the rule in `CHANGELOG.md` `[Unreleased]`. Done when a `### Changed` bullet names
      it.

## 2. Acceptance

- [ ] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
