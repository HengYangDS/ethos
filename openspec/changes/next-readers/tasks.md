# Tasks

## 1. Readers

- [ ] 1.1 Add `continuation` to the acceptance invocation helper and route the journey, lane and
      merge readers through it. Done when a test shows that it returns the typed argv of a command
      or a decision, returns nothing for prose, a template or a missing step, and never reads
      `next_action`, and when `local-install-smoke` passes.
- [ ] 1.2 Point the product Skill, the repository Skill and the quickstart at `next`. Done when the
      `skills` and docs gates pass with the Skill digest updated.

## 2. Acceptance

- [ ] 2.1 Pass lint, the delivery tests and readiness at the lane head. Done when each passes on the
      committed head.
