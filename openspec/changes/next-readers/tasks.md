# Tasks

## 1. Readers

- [x] 1.1 Add `continuation` to the acceptance invocation helper and route the journey, lane and
      merge readers through it. Done when a test shows that it returns the typed argv of a command
      or a decision, returns nothing for prose, a template or a missing step, and never reads
      `next_action`, and when `local-install-smoke` passes. At 00:23:09
      `test_a_reader_follows_only_a_typed_step_with_an_argv` passed. The first `local-install-smoke`
      at `cb1dd0203` failed at 00:21:40, because the lease and merge previews are decisions and a
      command-only helper returned nothing; after `01d364620` lets decisions through,
      `local-install-smoke` passed at 00:31:20.
- [x] 1.2 Point the product Skill, the repository Skill and the quickstart at `next`. Done when the
      `skills` and docs gates pass with the Skill digest updated. At 00:15:47 the readiness tier
      passed at `cb1dd0203`, among its 28 gates `skills`, `docs-registry`, `markdown-lint` and
      `prose`, with the repository Skill digest recomputed by the package digest owner; the 214
      delivery and Skill tests passed at 00:13:23.

## 2. Acceptance

- [x] 2.1 Pass lint, the delivery tests and readiness at the lane head. Done when each passes on the
      committed head. At 00:34:05 ruff, the format check and ty passed at `01d364620`,
      `local-install-smoke` passed there at 00:31:20, and readiness passed at `cb1dd0203` at
      00:15:47; the fix after it changed only the helper and its test.
